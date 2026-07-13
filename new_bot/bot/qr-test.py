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

def gen_html():
    with open('stations','r+', encoding="utf-8") as f:
        stations = f.readlines()

    with open('desc', 'r+', encoding="utf-8") as f: 
        desc = f.readlines()

    ans = ""
    for i in range(0, 17):
        ans += f"""
    <details>
        <summary>{stations[i].replace('\n','')}</summary>
        <p>{desc[i].replace('\n','')}</p>
    </details>
        """
    
    with open('fin', 'w+', encoding='utf-8') as f:
        f.write(ans)

if __name__ == "__main__":
    os.makedirs("./qrs_quiz", exist_ok=True) 
    gen_html()