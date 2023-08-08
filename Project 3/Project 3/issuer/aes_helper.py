
from Crypto.Cipher import AES


def gen_aes_key(hex_encoded=True):
    ''' Generates random 256-bit AES Key and writes to file '''
    ekey = os.urandom(32) # 256-bit key
    # print(f"AES key:\t{ekey}")

    # Write the key to file in hexadecimal format
    if hex_encoded:
        with open('./issuer.aes.key', 'w') as keyf:
            ekey_hex = ekey.hex()
            # Write hex string to file
            keyf.write(ekey_hex)
    else:
        with open('./issuer.aes.raw.key', 'wb') as keyf:
            keyf.write(ekey)


def read_aes_key(hex_encoded=True):
    ''' Reads AES Key from file '''
    if hex_encoded:
        with open('./issuer.aes.key', 'r') as keyf:
            ekey_hex = keyf.read()
            # Convert hex string to bytes
            ekey = bytes.fromhex(ekey_hex)
            # print({f"AES key:\t{ekey}"})
        return ekey
    else:
        with open('./issuer.aes.raw.key', 'rb') as keyf:
            ekey = keyf.read()
            # print({f"AES key:\t{ekey}"})
        return ekey
