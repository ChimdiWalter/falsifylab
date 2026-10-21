"""Create a one-page, evidence-first project overview from measured prototype results."""
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'drafts' / 'FalsifyLab_One_Page_Summary.pdf'
DATA = json.loads((ROOT / 'outputs' / 'results.json').read_text())
cases = {p['system']:p for p in DATA['cases']}
black = HexColor('#152338')
muted = HexColor('#4A5B6C')
accent = HexColor('#166284')
light = HexColor('#EAF1F4')

W,H=612,792
m=44
c=canvas.Canvas(str(OUT),pagesize=(W,H))
c.setTitle('FalsifyLab | OSI Hackathon 2026 | One-page scientific summary')
c.setAuthor('FalsifyLab')

def block(text,y, size=9.2, leading=13.6, color=black, width=W-2*m, bold=False):
    style = ParagraphStyle('p',fontName='Helvetica-Bold' if bold else 'Helvetica', fontSize=size,leading=leading,textColor=color,alignment=TA_LEFT,spaceBefore=0,spaceAfter=0)
    p=Paragraph(text,style)
    ww,hh=p.wrap(width,10000)
    p.drawOn(c,m,y-hh)
    return y-hh

c.setFillColor(accent); c.setFont('Helvetica-Bold',8.5)
c.drawString(m,H-43,'OSI HACKATHON 2026  /  SCIENTIFIC REASONING  /  SOLO PROTOTYPE')
c.setFillColor(black); c.setFont('Helvetica-Bold',26)
c.drawString(m,H-78,'FalsifyLab')
c.setFillColor(muted); c.setFont('Helvetica',12)
c.drawString(m,H-99,'Find a plausible law. Break it. Repair it. Test again.')
c.setStrokeColor(HexColor('#C9D9E2')); c.setLineWidth(.8)
c.line(m,H-112,W-m,H-112)
y=H-130

y=block('<b>Problem.</b> A scientific relationship can fit limited data yet fail under new experimental conditions. FalsifyLab explores a transparent <b>observe → propose → stress-test → revise → held-out audit</b> workflow for physical conservation-law candidates.',y)
y-=10
y=block('<b>Method.</b> Using only simulated position and velocity observations, a restricted learner fits <b>Q = v² + a·x²</b>. A fixed grid of 15 amplitude/horizon experiments searches for violations. After a counterexample, an optional <b>x^4</b> term is fitted and evaluated on a separate unseen trajectory.',y)
y-=14
# slim metric ribbon
c.setFillColor(light); c.roundRect(m,y-52,W-2*m,52,6,stroke=0,fill=1)
c.setFillColor(accent); c.setFont('Helvetica-Bold',9)
c.drawString(m+12,y-16,'NONLINEAR DUFFING OSCILLATOR: OBSERVED RELATIVE DRIFT')
c.setFillColor(black); c.setFont('Helvetica-Bold',18)
c.drawString(m+12,y-41,'0.59%')
c.setFont('Helvetica',9); c.drawString(m+76,y-40,'training')
c.setFont('Helvetica-Bold',17); c.drawString(m+186,y-41,'20.25%')
c.setFont('Helvetica',9); c.drawString(m+262,y-40,'held-out stress')
c.setFont('Helvetica-Bold',17); c.drawString(m+381,y-41,'~0%')
c.setFont('Helvetica',9); c.drawString(m+435,y-40,'revised')
y-=62

img=ImageReader(str(ROOT/'outputs'/'duffing_counterexample.png'))
imgw=490
imgh=imgw*(4.8/8.0)
c.drawImage(img,m+(W-2*m-imgw)/2,y-imgh,width=imgw,height=imgh)
y-=imgh+5

y=block('<b>Figure.</b> Independent synthetic Duffing trajectory: the quadratic hypothesis oscillates with time, while the revised quartic candidate remains constant within numerical solver precision.',y,size=8.3,leading=11.0,color=muted)
y-=10

y=block('<b>Evidence.</b> A harmonic oscillator preserves its quadratic candidate (~0% held-out drift). Duffing fails the original hypothesis (20.245%) but recovers a known relation, <b>Q = v² + 4x² + 0.5x^4</b>. In a weakly damped negative control, a quartic repair <b>still fails</b> (10.056% held-out drift). Four executable tests pass.',y,size=8.7,leading=12.2)
y-=9

y=block('<b>Scope and limitation.</b> These are noise-free synthetic demonstrations, not discoveries of new physics. The candidate family and search grid are hand-designed; the 2% drift threshold is heuristic rather than statistically calibrated. Surviving a test means <b>not refuted under tested conditions</b>, not proven true. General scientific-agent autonomy and real-world validation remain future work.',y,size=8.5,leading=12.1)
y-=10

y=block('<b>Research context.</b> Builds on established conservation-law identification, symbolic discovery, and agentic falsification ideas (e.g., SINDy 2016; sparse invariant detection 2024; POPPER 2025). Distinct contribution here is a small, reproducible, evidence-preserving falsification/repair demonstration.',y,size=8.1,leading=11.3,color=muted)
print('last text y',y)
c.setStrokeColor(HexColor('#CBD8E0'));c.line(m,42,W-m,42)
c.setFont('Helvetica',8);c.setFillColor(muted)
c.drawString(m,28,'Open Scientific Intelligence Hackathon | October 21–22, 2026')
c.drawRightString(W-m,28,'Reproduce: python -m falsifylab.run_demo')
c.save()
print('wrote',OUT)
