"""Render the application Markdown with embedded Korean fonts and live links.

Requires reportlab and static Noto Sans KR Regular/Bold TTF files. PDF generation
is separate from runtime dependencies and never invokes a language model.
"""
from __future__ import annotations
import argparse
from html import escape
import re
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
INK = colors.HexColor('#252522')
MUTED = colors.HexColor('#67665f')
ACCENT = colors.HexColor('#a33e22')


def inline(text):
    text = escape(text)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',
                  lambda m: f'<a href="{m[2]}" color="#a33e22">{m[1]}</a>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    return re.sub(r'`([^`]+)`', r'\1', text)


def styles():
    base = dict(fontName='NotoKR', textColor=INK, wordWrap='CJK', allowWidows=0, allowOrphans=0)
    return {
        'title': ParagraphStyle('title', **base, fontSize=26, leading=34, spaceAfter=13),
        'heading': ParagraphStyle('heading', **{**base, 'fontName':'NotoKR-Bold'}, fontSize=13,
                                  leading=20, spaceBefore=17, spaceAfter=9, keepWithNext=True),
        'body': ParagraphStyle('body', **base, fontSize=10.2, leading=17.2, spaceAfter=10),
        'meta': ParagraphStyle('meta', **{**base, 'textColor':MUTED}, fontSize=8.8, leading=14, spaceAfter=9),
        'table': ParagraphStyle('table', **base, fontSize=8.6, leading=13.8, spaceAfter=0),
        'th': ParagraphStyle('th', **{**base, 'fontName':'NotoKR-Bold', 'textColor':colors.white}, fontSize=8.6, leading=13.8),
        'bullet': ParagraphStyle('bullet', **base, fontSize=9.7, leading=16, leftIndent=10, firstLineIndent=-8, spaceAfter=6),
    }


def table(lines, sheet, width):
    rows = [[c.strip() for c in line.strip().strip('|').split('|')] for line in lines]
    rows = [row for row in rows if not all(re.fullmatch(r'[:\- ]+', cell or '-') for cell in row)]
    n = len(rows[0])
    ratios = {2:[.31,.69], 3:[.25,.29,.46], 4:[.43,.13,.20,.24]}.get(n,[1/n]*n)
    values = [[Paragraph(inline(c),sheet['th' if i==0 else 'table']) for c in row]
              for i,row in enumerate(rows)]
    result = LongTable(values,colWidths=[width*x for x in ratios],repeatRows=1,hAlign='LEFT')
    result.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#35352f')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f3ee')]),
        ('GRID',(0,0),(-1,-1),.5,colors.HexColor('#d9d9d9')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),
    ]))
    return result


def render(source, target, kind):
    text=source.read_text(encoding='utf-8')
    sheet=styles()
    doc=SimpleDocTemplate(str(target),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=50,bottomMargin=43,
                          title='윤기혁 자기소개서' if kind=='cover' else 'QueryScope 프로젝트 포트폴리오',author='윤기혁')
    story=[]
    kicker='MEDIAWILL NETWORKS / AI DEVELOPER' if kind=='cover' else 'PORTFOLIO / QUERY SCOPE'
    story.append(Paragraph(kicker,ParagraphStyle('kicker',fontName='NotoKR',fontSize=8,textColor=ACCENT,leading=12,spaceAfter=14)))
    lines=text.splitlines();i=0;section=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('# '):
            story.append(Paragraph(inline(line[2:]),sheet['title']));i+=1;continue
        if line.startswith('## '):
            section+=1
            if kind=='cover' and section==3:story.append(PageBreak())
            story.append(Paragraph(inline(line[3:]),sheet['heading']));i+=1;continue
        if line.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                block.append(lines[i]);i+=1
            story.extend([table(block,sheet,doc.width),Spacer(1,12)]);continue
        if line.startswith('- '):
            story.append(Paragraph('• '+inline(line[2:]),sheet['bullet']));i+=1;continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','- ')):
            paragraph.append(lines[i].strip());i+=1
        style=sheet['meta'] if section==0 else sheet['body']
        story.append(Paragraph(inline(' '.join(paragraph)),style))
    def page(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#d4d2ca'));canvas.setLineWidth(.4)
        canvas.line(44,33,A4[0]-44,33)
        canvas.setFont('NotoKR',7.4);canvas.setFillColor(MUTED)
        canvas.drawString(44,21,'윤기혁 / 알바천국 AI 개발자' if kind=='cover' else '윤기혁 / QueryScope / 2026-10-28')
        canvas.drawRightString(A4[0]-44,21,str(document.page))
        canvas.restoreState()
    doc.build(story,onFirstPage=page,onLaterPages=page)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('NotoKR',str(args.font_dir/'NotoSansKR-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('NotoKR-Bold',str(args.font_dir/'NotoSansKR-Bold.ttf')))
    pdfmetrics.registerFontFamily('NotoKR',normal='NotoKR',bold='NotoKR-Bold',italic='NotoKR',boldItalic='NotoKR-Bold')
    for source,name,kind in [('cover-letter.md','Yoon_Gihyeok_Alba_CoverLetter','cover'),
                             ('portfolio.md','Yoon_Gihyeok_KoSearch_Portfolio','portfolio')]:
        source=ROOT/'docs/application'/source
        (args.output/(name+'.md')).write_text(source.read_text(encoding='utf-8'),encoding='utf-8')
        render(source,args.output/(name+'.pdf'),kind)
        print(name)


if __name__=='__main__':main()
