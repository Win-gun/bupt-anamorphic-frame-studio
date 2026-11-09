"""Original designed 1536x864 raster fixture, NOT the user's event poster."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import math
root=Path(__file__).resolve().parents[1]
w,h=1536,864
im=Image.new('RGB',(w,h));pix=im.load()
for y in range(h):
 for x in range(w):
  glow=math.exp(-((x-1100)/550)**2-((y-320)/450)**2)
  pix[x,y]=(int(21+41*glow+y/h*8),int(9+14*glow),int(35+26*glow))
d=ImageDraw.Draw(im,'RGBA')
latin='/System/Library/Fonts/Supplemental/Arial.ttf'
cjk='/System/Library/Fonts/STHeiti Medium.ttc'
def font(size,chinese=False):
 try:return ImageFont.truetype(cjk if chinese else latin,size)
 except OSError:return ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',size)
# Stage lighting, curtain lines and an abstract performer silhouette.
for x in [920,1190,1420]:
 d.polygon([(x,70),(x-240,720),(x+130,720)],fill=(230,172,91,13))
for x in range(850,1510,32):d.line((x,65,x,755),fill=(231,177,100,14),width=2)
d.ellipse((1030,585,1500,820),fill=(207,132,50,30))
d.ellipse((1180,240,1265,325),fill=(10,5,22,255))
d.polygon([(1190,320),(1255,320),(1320,640),(1135,640)],fill=(13,6,26,255))
d.line((1220,380,1100,290),fill=(18,7,29,255),width=28)
d.line((1250,375,1340,330),fill=(18,7,29,255),width=23)
d.line((1315,315,1315,730),fill=(217,166,87,170),width=3)
for x,y,r in [(980,150,25),(1410,190,36),(1030,670,35),(880,730,23)]:
 d.polygon([(x,y-r),(x+8,y-7),(x+r,y-9),(x+15,y+8),(x+23,y+r),(x,y+17),(x-25,y+r),(x-14,y+5),(x-r,y-11),(x-7,y-6)],fill=(202,116,44,210))
d.rectangle((72,64,1464,800),outline=(221,179,110,120),width=2)
d.text((112,102),'BUPT / CULTURE & ARTS',font=font(23),fill='#dfc899')
d.text((105,225),'秋日序曲',font=font(116,True),fill='#f4dbac')
d.text((115,365),'AUTUMN RHYTHM',font=font(44),fill='#d7b97b')
d.line((118,462,720,462),fill='#b79761',width=2)
d.text((118,500),'校园音乐之夜 · 舞台与回声',font=font(29,True),fill='#e9d3b1')
d.text((118,568),'2026.11  /  19:00',font=font(29),fill='#d3af79')
d.text((118,725),'16:9 TEST ARTWORK / ORIGINAL RASTER FIXTURE',font=font(18),fill='#bfa581')
im.save(root/'examples/v2/poster-16x9.png')
