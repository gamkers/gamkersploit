import base64

def decode_base64(data):
    return base64.b64decode(data).decode()

def decrypt_code(code, times):
    for _ in range(times):
        code = decode_base64(code)
    return code
encrypted_code = """
"""
# Decrypt the code 10 times to retrieve the original
decrypted_code = decrypt_code(encrypted_code, 10)
# Execute the decrypt code
exec(decrypted_code)