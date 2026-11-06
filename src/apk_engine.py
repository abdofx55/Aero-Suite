"""
apk_engine.py — High-performance APK manifest inspection, parsing and patching.
Extracts package names from binary AXML and safely patches orientation/boot receivers.
"""
import os
import zipfile
import shutil
import re
import time
from core.i18n import t

BOOT_REPLACEMENTS = {
    # Standard Cold Boot actions
    "android.intent.action.BOOT_COMPLETED": "android.intent.action.BOOT_DISABLEDX",
    "android.intent.action.LOCKED_BOOT_COMPLETED": "android.intent.action.LOCKED_BOOT_DISABLEDX",
    "android.intent.action.ACTION_BOOT_COMPLETED": "android.intent.action.ACTION_BOOT_DISABLEDX",
    "android.intent.action.REBOOT": "android.intent.action.NOBOOT",
    # QuickBoot / Car Screen Turn-on actions
    "android.intent.action.QUICKBOOT_POWERON": "android.intent.action.QUICKBOOT_DISABLE",
    "com.htc.intent.action.QUICKBOOT_POWERON": "com.htc.intent.action.QUICKBOOT_DISABLE",
    "com.nwd.ACTION_AFTER_BOOT_COMPLETED": "com.nwd.ACTION_AFTER_BOOT_DISABLEDX",
    # Boot Permissions
    "android.permission.RECEIVE_BOOT_COMPLETED": "android.permission.RECEIVE_BOOT__DISABLED",
    "android.permission.QUICKBOOT_POWERON": "android.permission.QUICKBOOT_DISAB",
}


def get_apk_package_name(apk_path: str) -> str:
    """
    Parses AndroidManifest.xml binary format directly in memory without aapt.
    Extracts the root <manifest package="..."> attribute.
    """
    if not os.path.isfile(apk_path):
        return ""
    try:
        with zipfile.ZipFile(apk_path, 'r') as z:
            if "AndroidManifest.xml" not in z.namelist():
                return ""
            manifest_data = bytearray(z.read("AndroidManifest.xml"))

        if len(manifest_data) < 12 or manifest_data[0:4] != b'\x03\x00\x08\x00':
            return ""
        if manifest_data[8:12] != b'\x01\x00\x1c\x00':
            return ""

        sp_chunk_size = int.from_bytes(manifest_data[12:16], 'little')
        string_count = int.from_bytes(manifest_data[16:20], 'little')
        flags = int.from_bytes(manifest_data[24:28], 'little')
        string_start = int.from_bytes(manifest_data[28:32], 'little')

        is_utf8 = bool(flags & (1 << 8))
        string_data_start = 8 + string_start

        decoded_strings = {}
        package_str_idx = -1

        for i in range(string_count):
            off_ptr = 8 + 28 + (i * 4)
            offset = int.from_bytes(manifest_data[off_ptr:off_ptr+4], 'little')
            str_ptr = string_data_start + offset
            decoded = ""

            if is_utf8:
                u16_len = manifest_data[str_ptr]
                skip = 1
                if u16_len & 0x80: skip += 1
                u8_len = manifest_data[str_ptr + skip]
                skip += 1
                if u8_len & 0x80: skip += 1
                orig_len = u8_len & 0x7f
                content_ptr = str_ptr + skip
                str_bytes = manifest_data[content_ptr:content_ptr + orig_len]
                try:
                    decoded = str_bytes.decode('utf-8')
                    decoded_strings[i] = decoded
                except Exception:
                    continue
            else:
                u16_len = int.from_bytes(manifest_data[str_ptr:str_ptr+2], 'little')
                skip = 2
                if u16_len & 0x8000: skip += 2
                orig_len = u16_len & 0x7fff
                content_ptr = str_ptr + skip
                str_bytes = manifest_data[content_ptr:content_ptr + orig_len * 2]
                try:
                    decoded = str_bytes.decode('utf-16-le')
                    decoded_strings[i] = decoded
                except Exception:
                    continue

            if decoded == "package":
                package_str_idx = i

        if package_str_idx == -1:
            return ""

        ptr = 8 + sp_chunk_size
        if ptr + 4 < len(manifest_data) and manifest_data[ptr:ptr+4] == b'\x80\x01\x08\x00':
            rm_size = int.from_bytes(manifest_data[ptr+4:ptr+8], 'little')
            ptr += rm_size

        while ptr + 8 <= len(manifest_data):
            chunk_type = int.from_bytes(manifest_data[ptr:ptr+2], 'little')
            chunk_size = int.from_bytes(manifest_data[ptr+4:ptr+8], 'little')
            if chunk_size <= 0:
                break

            if chunk_type == 0x0102:  # Start Element
                attr_start = int.from_bytes(manifest_data[ptr+24:ptr+26], 'little')
                attr_size = int.from_bytes(manifest_data[ptr+26:ptr+28], 'little')
                attr_count = int.from_bytes(manifest_data[ptr+28:ptr+30], 'little')

                attr_array_ptr = ptr + 16 + attr_start
                for j in range(attr_count):
                    single_attr_ptr = attr_array_ptr + (j * attr_size)
                    if single_attr_ptr + 20 > len(manifest_data):
                        break
                    attr_name_idx = int.from_bytes(manifest_data[single_attr_ptr+4:single_attr_ptr+8], 'little')
                    if attr_name_idx == package_str_idx:
                        attr_data = int.from_bytes(manifest_data[single_attr_ptr+16:single_attr_ptr+20], 'little')
                        if attr_data in decoded_strings:
                            return decoded_strings[attr_data]
            ptr += chunk_size
    except Exception:
        pass
    return ""


def clean_app_display_name(filename: str) -> str:
    """Produces a clean readable title from an APK filename."""
    base = os.path.splitext(filename)[0]
    base = re.sub(r'[\-_]', ' ', base)
    base = re.sub(r'\(.*?\)', '', base)
    base = re.sub(r'\[.*?\]', '', base)
    base = re.sub(r'\s+', ' ', base).strip()
    return base


# In-memory stat cache to make rescanning instantaneous (sub-millisecond)
_APK_METADATA_CACHE = {}


def scan_local_apks(apks_dir: str) -> list:
    """
    Scans the local apks folder and returns detailed metadata for all valid APKs.
    Leverages filesystem mtime and file size caching for instantaneous rescanning.
    """
    if not os.path.isdir(apks_dir):
        return []

    results = []
    for fname in sorted(os.listdir(apks_dir)):
        if fname.lower().endswith(".apk"):
            fpath = os.path.join(apks_dir, fname)
            try:
                st = os.stat(fpath)
                cache_key = (fpath, st.st_mtime, st.st_size)
                if cache_key in _APK_METADATA_CACHE:
                    results.append(_APK_METADATA_CACHE[cache_key])
                    continue

                size_mb = st.st_size / (1024 * 1024)
                pkg = get_apk_package_name(fpath)
                display = clean_app_display_name(fname)
                item = {
                    "filename": fname,
                    "path": fpath,
                    "package": pkg or "unknown.package",
                    "display_name": display or fname,
                    "size_mb": round(size_mb, 1),
                }
                _APK_METADATA_CACHE[cache_key] = item
                results.append(item)
            except Exception:
                continue
    return results


def patch_apk(input_apk_path: str, output_apk_path: str, log_func=None, target_orientation="default", disable_boot_launch=True, progress_callback=None):
    """
    Patches screenOrientation and/or disables auto-boot receivers inside the APK's AndroidManifest.xml.
    target_orientation: "portrait" (1), "landscape" (0), or "default" (no change)
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    needs_patch = (target_orientation == "portrait") or disable_boot_launch
    if not needs_patch:
        shutil.copy2(input_apk_path, output_apk_path)
        return True

    _log(t("logs.apk_patcher_analyzing", f"  Patcher analyzing: {os.path.basename(input_apk_path)} (Portrait={target_orientation == 'portrait'}, BootBlock={disable_boot_launch})...", name=os.path.basename(input_apk_path), portrait=(target_orientation == 'portrait'), boot_block=disable_boot_launch))
    try:
        with zipfile.ZipFile(input_apk_path, 'r') as z_in:
            if "AndroidManifest.xml" not in z_in.namelist():
                _log(t("logs.apk_manifest_missing", "  [!] No AndroidManifest.xml found, copying as-is."))
                shutil.copy2(input_apk_path, output_apk_path)
                return True
            manifest_data = bytearray(z_in.read("AndroidManifest.xml"))

        if len(manifest_data) < 12 or manifest_data[0:4] != b'\x03\x00\x08\x00':
            shutil.copy2(input_apk_path, output_apk_path)
            return True

        sp_chunk_size = int.from_bytes(manifest_data[12:16], 'little')
        string_count = int.from_bytes(manifest_data[16:20], 'little')
        flags = int.from_bytes(manifest_data[24:28], 'little')
        string_start = int.from_bytes(manifest_data[28:32], 'little')
        is_utf8 = bool(flags & (1 << 8))
        string_data_start = 8 + string_start

        modified = False
        screen_orientation_str_idx = -1
        decoded_strings = {}

        # 1. Read String Pool & patch boot receivers
        for i in range(string_count):
            off_ptr = 8 + 28 + (i * 4)
            offset = int.from_bytes(manifest_data[off_ptr:off_ptr+4], 'little')
            str_ptr = string_data_start + offset
            decoded = ""

            if is_utf8:
                u16_len = manifest_data[str_ptr]
                skip = 1
                if u16_len & 0x80: skip += 1
                u8_len = manifest_data[str_ptr + skip]
                skip += 1
                if u8_len & 0x80: skip += 1
                orig_len = u8_len & 0x7f
                content_ptr = str_ptr + skip
                str_bytes = manifest_data[content_ptr:content_ptr + orig_len]
                try:
                    decoded = str_bytes.decode('utf-8')
                    decoded_strings[i] = decoded
                except Exception:
                    continue
            else:
                u16_len = int.from_bytes(manifest_data[str_ptr:str_ptr+2], 'little')
                skip = 2
                if u16_len & 0x8000: skip += 2
                orig_len = u16_len & 0x7fff
                content_ptr = str_ptr + skip
                str_bytes = manifest_data[content_ptr:content_ptr + orig_len * 2]
                try:
                    decoded = str_bytes.decode('utf-16-le')
                    decoded_strings[i] = decoded
                except Exception:
                    continue

            if decoded == "screenOrientation":
                screen_orientation_str_idx = i

            if disable_boot_launch:
                new_str = None
                if decoded in BOOT_REPLACEMENTS:
                    new_str = BOOT_REPLACEMENTS[decoded]
                elif "BOOT_COMPLETED" in decoded:
                    new_str = decoded.replace("BOOT_COMPLETED", "BOOT_DISABLED")
                elif "QUICKBOOT" in decoded:
                    new_str = decoded.replace("QUICKBOOT", "NOQUICKBT")
                elif "RECEIVE_BOOT" in decoded:
                    new_str = decoded.replace("RECEIVE_BOOT", "NO_RECV_BOOT")

                if new_str:
                    if len(new_str) < len(decoded):
                        new_str += "X" * (len(decoded) - len(new_str))
                    elif len(new_str) > len(decoded):
                        new_str = new_str[:len(decoded)]

                    if is_utf8:
                        manifest_data[content_ptr:content_ptr + orig_len] = new_str.encode('utf-8')
                    else:
                        manifest_data[content_ptr:content_ptr + orig_len * 2] = new_str.encode('utf-16-le')
                    decoded_strings[i] = new_str
                    modified = True

        # 2. Parse Resource Map for screenOrientation (0x0101001e)
        ptr = 8 + sp_chunk_size
        if ptr + 4 < len(manifest_data) and manifest_data[ptr:ptr+4] == b'\x80\x01\x08\x00':
            rm_size = int.from_bytes(manifest_data[ptr+4:ptr+8], 'little')
            rm_count = (rm_size - 8) // 4
            for i in range(rm_count):
                res_id = int.from_bytes(manifest_data[ptr+8+(i*4):ptr+12+(i*4)], 'little')
                if res_id == 0x0101001e:
                    screen_orientation_str_idx = i
            ptr += rm_size

        # 3. Patch XML Element Attributes for screenOrientation
        if target_orientation == "portrait" and screen_orientation_str_idx != -1:
            while ptr + 8 <= len(manifest_data):
                chunk_type = int.from_bytes(manifest_data[ptr:ptr+2], 'little')
                chunk_size = int.from_bytes(manifest_data[ptr+4:ptr+8], 'little')
                if chunk_size <= 0:
                    break

                if chunk_type == 0x0102:  # Start Element
                    attr_start = int.from_bytes(manifest_data[ptr+24:ptr+26], 'little')
                    attr_size = int.from_bytes(manifest_data[ptr+26:ptr+28], 'little')
                    attr_count = int.from_bytes(manifest_data[ptr+28:ptr+30], 'little')

                    attr_array_ptr = ptr + 16 + attr_start
                    for j in range(attr_count):
                        single_attr_ptr = attr_array_ptr + (j * attr_size)
                        if single_attr_ptr + 20 > len(manifest_data):
                            break
                        attr_name_idx = int.from_bytes(manifest_data[single_attr_ptr+4:single_attr_ptr+8], 'little')
                        if attr_name_idx == screen_orientation_str_idx:
                            # 1 = portrait
                            manifest_data[single_attr_ptr+12:single_attr_ptr+16] = (0x10000008).to_bytes(4, 'little')
                            manifest_data[single_attr_ptr+16:single_attr_ptr+20] = (1).to_bytes(4, 'little')
                            modified = True
                ptr += chunk_size

        if modified:
            _log(t("logs.apk_manifest_patched", "  ✓ Successfully patched manifest (AXML modified)."))
            if progress_callback:
                progress_callback(0.0, "repack")
            with zipfile.ZipFile(input_apk_path, 'r') as z_in, zipfile.ZipFile(output_apk_path, 'w', compression=zipfile.ZIP_DEFLATED) as z_out:
                items = z_in.infolist()
                total_items = max(1, len(items))
                last_t = time.time()
                for idx, item in enumerate(items):
                    if item.filename.startswith("META-INF/"):
                        continue  # Strip old signatures so modified AXML is accepted
                    if item.filename == "AndroidManifest.xml":
                        z_out.writestr(item, manifest_data)
                    else:
                        z_out.writestr(item, z_in.read(item.filename), compress_type=item.compress_type)
                    if progress_callback and (idx % 8 == 0 or time.time() - last_t > 0.06):
                        last_t = time.time()
                        progress_callback(0.35 * (idx / total_items), "repack")

            # Automatically apply Android v1 signature and 4096-byte page alignment
            def _sign_cb(frac):
                if progress_callback:
                    progress_callback(0.35 + 0.40 * frac, "sign")

            sign_apk(output_apk_path, log_func=log_func, progress_callback=_sign_cb, run_zipalign=False)

            def _align_cb(frac):
                if progress_callback:
                    progress_callback(0.75 + 0.25 * frac, "align")

            zipalign_apk(output_apk_path, log_func=log_func, progress_callback=_align_cb)
            if progress_callback:
                progress_callback(1.0, "done")
        else:
            shutil.copy2(input_apk_path, output_apk_path)
            if progress_callback:
                progress_callback(1.0, "done")

        return True
    except Exception as e:
        _log(t("logs.apk_patch_error", f"  [!] Patching error ({e}), deploying original APK.", err=str(e)))
        try:
            shutil.copy2(input_apk_path, output_apk_path)
            return True
        except Exception:
            return False


def sign_apk(apk_path: str, log_func=None, progress_callback=None, run_zipalign=True) -> bool:
    """
    Signs the APK in-place with a standard Android v1 (JAR) RSA signature
    using pure Python (cryptography), without requiring Java, jarsigner, or debug.keystore.
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    temp_apk = apk_path + ".signing.tmp"
    try:
        import hashlib
        import base64
        import datetime
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import pkcs7, Encoding

        manifest_lines = [
            "Manifest-Version: 1.0",
            "Created-By: 1.0 (Aero Suite Studio)"
        ]
        file_digests = {}

        # 1. Read existing APK files and compute SHA-256 digests
        with zipfile.ZipFile(apk_path, 'r') as z_in:
            names = sorted(z_in.namelist())
            total_items = max(1, len(names))
            last_t = time.time()
            for idx, item in enumerate(names):
                if item.startswith("META-INF/"):
                    continue
                data = z_in.read(item)
                d = base64.b64encode(hashlib.sha256(data).digest()).decode('ascii')
                file_digests[item] = d
                manifest_lines.append("")
                manifest_lines.append(f"Name: {item}")
                manifest_lines.append(f"SHA-256-Digest: {d}")
                if progress_callback and (idx % 8 == 0 or time.time() - last_t > 0.06):
                    last_t = time.time()
                    progress_callback(0.50 * (idx / total_items))

        manifest_content = "\r\n".join(manifest_lines) + "\r\n"
        manifest_bytes = manifest_content.encode('utf-8')
        manifest_digest = base64.b64encode(hashlib.sha256(manifest_bytes).digest()).decode('ascii')

        # 2. Build CERT.SF
        sf_lines = [
            "Signature-Version: 1.0",
            "Created-By: 1.0 (Aero Suite Studio)",
            f"SHA-256-Digest-Manifest: {manifest_digest}"
        ]
        for name, d in file_digests.items():
            entry = f"Name: {name}\r\nSHA-256-Digest: {d}\r\n".encode('utf-8')
            ed = base64.b64encode(hashlib.sha256(entry).digest()).decode('ascii')
            sf_lines.append("")
            sf_lines.append(f"Name: {name}")
            sf_lines.append(f"SHA-256-Digest: {ed}")

        sf_content = "\r\n".join(sf_lines) + "\r\n"
        sf_bytes = sf_content.encode('utf-8')

        # 3. Generate self-signed RSA debug cert
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cert_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Android Debug')])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(cert_name)
            .issuer_name(cert_name)
            .public_key(key.public_key())
            .serial_number(1)
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=10000))
            .sign(key, hashes.SHA256())
        )

        # 4. Generate PKCS#7 detached signature block for CERT.RSA without S/MIME attributes
        builder = pkcs7.PKCS7SignatureBuilder().set_data(sf_bytes)
        sig_der = builder.add_signer(cert, key, hashes.SHA256()).sign(
            Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.NoAttributes]
        )

        # 5. Write everything into temp APK and replace original
        with zipfile.ZipFile(apk_path, 'r') as z_in, zipfile.ZipFile(temp_apk, 'w', compression=zipfile.ZIP_DEFLATED) as z_out:
            # First write signature files in META-INF/ (Android standard convention)
            z_out.writestr("META-INF/MANIFEST.MF", manifest_bytes)
            z_out.writestr("META-INF/CERT.SF", sf_bytes)
            z_out.writestr("META-INF/CERT.RSA", sig_der)

            # Then copy the rest of the files
            infolist = z_in.infolist()
            total_copy = max(1, len(infolist))
            last_t = time.time()
            for idx, item in enumerate(infolist):
                if item.filename.startswith("META-INF/"):
                    continue
                z_out.writestr(item, z_in.read(item.filename), compress_type=item.compress_type)
                if progress_callback and (idx % 8 == 0 or time.time() - last_t > 0.06):
                    last_t = time.time()
                    progress_callback(0.50 + 0.50 * (idx / total_copy))

        shutil.move(temp_apk, apk_path)
        if run_zipalign:
            zipalign_apk(apk_path, log_func=log_func)
        _log(t("logs.apk_signed_success", "  ✓ APK signed successfully (v1 signature applied)."))
        if progress_callback:
            progress_callback(1.0)
        return True
    except Exception as e:
        _log(t("logs.apk_sign_failed", f"  [!] Failed to sign APK: {e}", err=str(e)))
        if os.path.exists(temp_apk):
            try:
                os.remove(temp_apk)
            except Exception:
                pass
        return False


def zipalign_apk(apk_path: str, log_func=None, progress_callback=None) -> bool:
    """
    Performs 4096-byte page alignment on uncompressed native libraries (.so)
    and 4-byte alignment on uncompressed resources using pure Python.
    Prevents 'INSTALL_FAILED_INVALID_APK: Failed to extract native libraries, res=-2'
    on Android 8.1/9 when android:extractNativeLibs='false'.
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    aligned_apk = apk_path + ".aligned.tmp"
    try:
        import struct
        with zipfile.ZipFile(apk_path, 'r') as z_in, open(apk_path, 'rb') as f_raw, open(aligned_apk, 'wb') as f_out:
            entries = []
            for info in z_in.infolist():
                f_raw.seek(info.header_offset + 26)
                fn_len, extra_len = struct.unpack('<HH', f_raw.read(4))
                data_start = info.header_offset + 30 + fn_len + extra_len
                f_raw.seek(data_start)
                raw_data = f_raw.read(info.compress_size)
                entries.append((info, raw_data))

            total_entries = max(1, len(entries))
            last_t = time.time()
            central_dir_entries = []
            for idx, (info, raw_data) in enumerate(entries):
                header_offset = f_out.tell()
                fname_bytes = info.filename.encode('utf-8')
                align = 4
                if info.filename.endswith('.so') and info.compress_type == zipfile.ZIP_STORED:
                    align = 4096
                elif info.compress_type != zipfile.ZIP_STORED:
                    align = 1

                base_header_len = 30 + len(fname_bytes)
                existing_extra = info.extra or b''
                unaligned_data_offset = header_offset + base_header_len + len(existing_extra)
                padding_len = (align - (unaligned_data_offset % align)) % align if align > 1 else 0
                extra = existing_extra + (b'\x00' * padding_len)

                header = struct.pack(
                    '<IHHHHHIIIHH',
                    0x04034b50, info.extract_version, info.flag_bits, info.compress_type,
                    info.date_time[3] << 11 | info.date_time[4] << 5 | info.date_time[5] // 2,
                    (info.date_time[0] - 1980) << 9 | info.date_time[1] << 5 | info.date_time[2],
                    info.CRC, info.compress_size, info.file_size, len(fname_bytes), len(extra)
                )
                f_out.write(header)
                f_out.write(fname_bytes)
                f_out.write(extra)
                f_out.write(raw_data)
                central_dir_entries.append((info, fname_bytes, extra, header_offset))
                if progress_callback and (idx % 10 == 0 or time.time() - last_t > 0.06):
                    last_t = time.time()
                    progress_callback(idx / total_entries)

            cd_start = f_out.tell()
            for info, fname_bytes, extra, header_offset in central_dir_entries:
                cd_header = struct.pack(
                    '<IHHHHHHIIIHHHHHII',
                    0x02014b50, info.create_version, info.extract_version, info.flag_bits, info.compress_type,
                    info.date_time[3] << 11 | info.date_time[4] << 5 | info.date_time[5] // 2,
                    (info.date_time[0] - 1980) << 9 | info.date_time[1] << 5 | info.date_time[2],
                    info.CRC, info.compress_size, info.file_size, len(fname_bytes), len(extra),
                    len(info.comment or b''), 0, info.internal_attr, info.external_attr, header_offset
                )
                f_out.write(cd_header)
                f_out.write(fname_bytes)
                f_out.write(extra)
                if info.comment:
                    f_out.write(info.comment)

            cd_end = f_out.tell()
            cd_size = cd_end - cd_start
            eocd = struct.pack(
                '<IHHHHIIH',
                0x06054b50, 0, 0, len(central_dir_entries), len(central_dir_entries),
                cd_size, cd_start, 0
            )
            f_out.write(eocd)

        shutil.move(aligned_apk, apk_path)
        _log(t("logs.apk_zipaligned_success", "  ✓ APK zipaligned (native libraries 4096-byte page aligned)."))
        if progress_callback:
            progress_callback(1.0)
        return True
    except Exception as e:
        _log(t("logs.apk_zipalign_failed", f"  [!] Failed to zipalign APK: {e}", err=str(e)))
        if os.path.exists(aligned_apk):
            try:
                os.remove(aligned_apk)
            except Exception:
                pass
        return False
