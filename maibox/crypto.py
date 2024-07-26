from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

import maibox.config as config


class CipherAES:
    BLOCK_SIZE = 128
    KEY_SIZE = 256
    AES_KEY = bytes.fromhex(config.get_config()["aes_key"])
    AES_IV = bytes.fromhex(config.get_config()["aes_iv"])

    @staticmethod
    def _pad(data):
        block_size = CipherAES.BLOCK_SIZE // 8
        padding_length = block_size - len(data) % block_size
        return data + bytes([padding_length]) * padding_length

    @staticmethod
    def _unpad(padded_data):
        pad_char = padded_data[-1]
        if not 1 <= pad_char <= CipherAES.BLOCK_SIZE // 8:
            raise ValueError("Invalid padding")
        return padded_data[:-pad_char]

    @classmethod
    def encrypt(cls, plaintext):
        backend = default_backend()
        cipher = Cipher(algorithms.AES(cls.AES_KEY), modes.CBC(cls.AES_IV), backend=backend)
        encryptor = cipher.encryptor()

        padded_plaintext = cls._pad(plaintext)
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
        return ciphertext

    @classmethod
    def decrypt(cls, ciphertext):
        backend = default_backend()
        cipher = Cipher(algorithms.AES(cls.AES_KEY), modes.CBC(cls.AES_IV), backend=backend)
        decryptor = cipher.decryptor()

        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()
        return cls._unpad(decrypted_data)

