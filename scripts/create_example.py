from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parents[1]
im=Image.new('RGB',(1000,1400),'#eee9dc')
d=ImageDraw.Draw(im)
font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(n):
    try: return ImageFont.truetype(font_path,n)
    except OSError: return ImageFont.load_default()
d.rectangle((65,65,935,1335),outline='#193d46',width=3)
d.text((100,100),'BUPT / 2026',font=font(42),fill='#193d46')
d.text((100,250),'BEYOND',font=font(115),fill='#193d46')
d.text((100,375),'THE FRAME',font=font(98),fill='#193d46')
for r in range(280,40,-12):
    d.ellipse((500-r,820-r,500+r,820+r),outline='#bd5b2e',width=4)
d.line((100,1150,900,1150),fill='#193d46',width=3)
d.text((100,1190),'ART / SCIENCE / CONNECTION',font=font(33),fill='#193d46')
d.text((100,1250),'Original raster typography. No AI redraw.',font=font(23),fill='#193d46')
im.save(root/'examples/poster.png')
