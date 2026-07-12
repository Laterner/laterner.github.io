import qrcode # pillow
import os


def generate(user_id: str):
    img = qrcode.make(user_id)
    type(img)  # qrcode.image.pil.PilImage
    img.save(f"./qrs_quiz/{user_id}.png")


secrets = [
    'DSFGS',
    'CACTD',
    'FXZJN',
    'VGNMD',
    'UZQYX',
    'KBCFL',
    'XTHFL',
    'EGLPZ',
    'SQVEP',
    'MLKGL'
]

if __name__ == "__main__":
    os.makedirs("./qrs_quiz", exist_ok=True) 
    for el in secrets:
        generate(el)