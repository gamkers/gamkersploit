import base64

def encode_base64(data):
    """Encode the data using base64."""
    return base64.b64encode(data.encode())

def decode_base64(data):
    """Decode the base64 encoded data."""
    return base64.b64decode(data).decode()

def encrypt_code(code, times):
    """Encrypt the code by encoding it in base64 'times' times."""
    for _ in range(times):
        code = encode_base64(code).decode()
    return code

def decrypt_code(code, times):
    """Decrypt the code by decoding it in base64 'times' times."""
    for _ in range(times):
        code = decode_base64(code)
    return code

# Sample code to encrypt
original_code = r'''
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

'''
# Encrypt the code 10 times
encrypted_code = encrypt_code(original_code, 10)
print("Encrypted code:")
# print(encrypted_code)

with open("encrypted_code.txt", "w") as file:
    file.write(encrypted_code)

# # Decrypt the code 10 times to retrieve the original
# decrypted_code = decrypt_code(encrypted_code, 10)
# print("\nDecrypted code:")
# print(decrypted_code)