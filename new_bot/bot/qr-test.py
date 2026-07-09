import qrcode # pillow
import os


async def generate(user_id: str):
    img = qrcode.make(user_id)
    type(img)  # qrcode.image.pil.PilImage
    img.save(f"./static/user_qrs/{user_id}.png")

if __name__ == "__main__":
    os.makedirs("./static/user_qrs", exist_ok=True) 
    generate("W8R0B")