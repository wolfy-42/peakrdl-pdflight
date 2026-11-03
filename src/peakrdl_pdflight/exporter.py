#--------------------------------------------------------------------------------------------------
#
# SPDX-License-Identifier: Apache-2.0 OR MIT
#
# Project      : FPGA Project Template
# Author       : DV
# Created      : 2026-11-02
#--------------------------------------------------------------------------------------------------
# Description  : PdfExporter: writes a compiled SystemRDL register map as a PDF with reportlab.
#                Layout: title page (if there is a title), table of contents, then one numbered
#                section per addrmap/regfile/mem/register (top = 1, children 1.x, 1.x.y, ...).
#                Every heading is "<num> <absolute address> <instance name> Size: <size>" (the top
#                has no address); blocks list their children in a linked table, memories show
#                their width and entries, registers show a bit drawing and a field table.
#                All hex numbers use capital digits; addresses are padded to the widest one.
# Updated      : yyyy-mm-dd / author - comments
#--------------------------------------------------------------------------------------------------

from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate,
                                Paragraph, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents
from systemrdl.node import AddressableNode, MemNode, RegNode

PAGE_SIZES = {"letter": letter, "a4": A4}
MARGIN = 0.75 * inch
LINK_COLOR = "#1F4E9E"
FONT, BOLD = "Helvetica", "Helvetica-Bold"

# look of every table: thin grid, grey bold header row, small font
TABLE_STYLE = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ("FONTNAME", (0, 0), (-1, 0), BOLD),
    ("FONTNAME", (0, 1), (-1, -1), FONT),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
])


def hx(value, digits=0):
    """Hex with capital digits and a 0x prefix, zero-padded to digits."""
    return "0x%0*X" % (digits, value)


def prop_text(node, prop):
    """The name or desc property as one line of text, "" if it is not set (never the default
    instance name)."""
    value = node.get_property(prop, default=None)
    return " ".join(value.split()) if value else ""


def page_canvas(title):
    """Canvas class that draws the header (title) and footer ("Page N of M") on every page.
    The pages are kept until the end so the total page count is known."""
    class PageCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            for page in self._pages:
                self.__dict__.update(page)
                width, height = self._pagesize
                self.setFont(FONT, 8)
                self.setFillColor(colors.grey)
                if title:
                    self.drawString(MARGIN, height - MARGIN / 2, title)
                self.drawCentredString(width / 2, MARGIN / 2,
                                       "Page %d of %d" % (self._pageNumber, len(self._pages)))
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)
    return PageCanvas


class Doc(BaseDocTemplate):
    """Document that turns every heading into a PDF bookmark and a table of contents entry."""
    def afterFlowable(self, flowable):
        key = getattr(flowable, "toc_key", None)
        if key:
            self.canv.addOutlineEntry(flowable.toc_text, key, flowable.toc_level,
                                      closed=flowable.toc_level > 0)
            self.notify("TOCEntry", (flowable.toc_level, escape(flowable.toc_text), self.page, key))


class PdfExporter:
    def export(self, top_node, path, title=None, page_size="letter"):
        """Write the register map below top_node (an AddrmapNode) as a PDF to path."""
        if title is None:
            title = prop_text(top_node, "name") or prop_text(top_node, "desc")

        # address digits: enough for the widest absolute address in the map
        nodes = [n for n in top_node.descendants(unroll=True) if isinstance(n, AddressableNode)]
        self.digits = len("%X" % max([n.absolute_address for n in nodes] + [0]))

        doc = Doc(path, pagesize=PAGE_SIZES[page_size], leftMargin=MARGIN, rightMargin=MARGIN,
                  topMargin=MARGIN, bottomMargin=MARGIN, title=title, author="")
        doc.addPageTemplates([PageTemplate(id="page", frames=[
            Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="frame")])])
        self.width = doc.width

        base = getSampleStyleSheet()
        self.body = ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9)
        self.cell = ParagraphStyle("cell", fontName=FONT, fontSize=8, leading=10)
        self.links_style = ParagraphStyle("links", fontName=FONT, fontSize=7, alignment=2)
        self.heads = [ParagraphStyle("h%d" % i, parent=base["Heading%d" % (i + 1)], fontName=BOLD,
                                     fontSize=size, leading=size * 1.25, keepWithNext=1)
                      for i, size in enumerate([16, 13, 11, 10])]
        toc = TableOfContents()
        toc.levelStyles = [ParagraphStyle("toc%d" % i, fontName=FONT, fontSize=9, leading=12,
                                          leftIndent=12 * i, firstLineIndent=0)
                           for i in range(8)]

        self.story = []
        if title:
            self.story += [Paragraph(escape(title), base["Title"]), PageBreak()]
        self.story += [Paragraph('<a name="toc"/>Contents', self.heads[0]), toc, PageBreak()]
        self.section(top_node, "1", None, 0)
        doc.multiBuild(self.story, canvasmaker=page_canvas(title))

    def addr(self, node):
        return hx(node.absolute_address, self.digits)

    def link(self, key, label):
        return '<a href="#%s" color="%s">%s</a>' % (key, LINK_COLOR, escape(label))

    def section(self, node, num, parent_key, level):
        """Add the numbered section of node, then (for blocks) the sections of its children."""
        key = "s" + num.replace(".", "_")
        if parent_key is None:
            head = "%s %s Size: %s" % (num, node.inst_name, hx(node.size))
        else:
            head = "%s %s %s Size: %s" % (num, self.addr(node), node.get_path_segment(), hx(node.size))
        heading = Paragraph('<a name="%s"/>%s' % (key, escape(head)), self.heads[min(level, 3)])
        heading.toc_key, heading.toc_text, heading.toc_level = key, head, level

        links = [self.link(parent_key, "up")] if parent_key else []
        flow = [heading, Paragraph(" &nbsp; ".join(links + [self.link("toc", "back to top")]),
                                   self.links_style)]
        desc = prop_text(node, "desc")
        if desc:
            flow.append(Paragraph(escape(desc), self.body))

        if isinstance(node, RegNode):
            flow += [self.reg_drawing(node), self.field_table(node)]
            self.story.append(KeepTogether(flow))
            return
        if isinstance(node, MemNode):
            flow.append(self.table([["Width (bits)", "Entries"],
                                    [str(node.get_property("memwidth")),
                                     hx(node.get_property("mementries"))]], [1.2 * inch] * 2))
            self.story.append(KeepTogether(flow))
            return

        # addrmap / regfile: table of the children, each linked to its own section
        children = [c for c in node.children(unroll=True) if isinstance(c, AddressableNode)]
        rows = [["Address", "Identifier", "Size", "Description"]]
        for i, child in enumerate(children, 1):
            child_key = "s" + ("%s.%d" % (num, i)).replace(".", "_")
            rows.append([self.addr(child),
                         Paragraph(self.link(child_key, child.get_path_segment()), self.cell),
                         hx(child.size), Paragraph(escape(prop_text(child, "desc")), self.cell)])
        if children:
            flow.append(self.table(rows, [1.1 * inch, 1.6 * inch, 0.9 * inch, None]))
        self.story += flow
        for i, child in enumerate(children, 1):
            self.section(child, "%s.%d" % (num, i), key, level + 1)

    def table(self, rows, col_widths):
        """A table filling the page width (a None column width takes the rest)."""
        rest = self.width - sum(w for w in col_widths if w)
        table = Table(rows, colWidths=[w or rest for w in col_widths], repeatRows=1, hAlign="LEFT")
        table.setStyle(TABLE_STYLE)
        return table

    def segments(self, reg):
        """(msb, lsb, field) for the fields and unused bit ranges (field None), highest first."""
        result, bit = [], reg.get_property("regwidth") - 1
        for field in sorted(reg.fields(), key=lambda f: f.msb, reverse=True):
            if field.msb < bit:
                result.append((bit, field.msb + 1, None))
            result.append((field.msb, field.lsb, field))
            bit = field.lsb - 1
        if bit >= 0:
            result.append((bit, 0, None))
        return result

    def reg_drawing(self, reg):
        """Bit layout: rows of 32 bits (highest row on top), one box per field, bit numbers
        above the box edges, unused bits grey."""
        regwidth = reg.get_property("regwidth")
        bit_w, box_h, label_h = self.width / 32, 16, 9
        row_h = box_h + label_h + 4
        rows = list(range(regwidth - 1, -1, -32))
        drawing = Drawing(self.width, row_h * len(rows))
        for r, row_hi in enumerate(rows):
            row_lo = max(row_hi - 31, 0)
            y = row_h * (len(rows) - 1 - r) + 2
            for msb, lsb, field in self.segments(reg):
                hi, lo = min(msb, row_hi), max(lsb, row_lo)
                if hi < lo:
                    continue
                x, w = (row_hi - hi) * bit_w, (hi - lo + 1) * bit_w
                drawing.add(Rect(x, y, w, box_h, strokeColor=colors.black, strokeWidth=0.5,
                                 fillColor=colors.white if field else colors.lightgrey))
                drawing.add(String(x + 1, y + box_h + 2, str(hi), fontName=FONT, fontSize=6))
                if lo != hi:
                    drawing.add(String(x + w - 1, y + box_h + 2, str(lo), fontName=FONT,
                                       fontSize=6, textAnchor="end"))
                if field:
                    name, size = field.inst_name, 7.0
                    while stringWidth(name, FONT, size) > w - 2 and size > 4:
                        size -= 0.5
                    while name and stringWidth(name, FONT, size) > w - 2:
                        name = name[:-1]
                    drawing.add(String(x + w / 2, y + 5, name, fontName=FONT, fontSize=size,
                                       textAnchor="middle"))
        return drawing

    def field_table(self, reg):
        rows = [["Bits", "Name", "SW access", "HW access", "Reset", "Description"]]
        for msb, lsb, field in self.segments(reg):
            bits = "[%d:%d]" % (msb, lsb) if msb != lsb else "[%d]" % msb
            if field is None:
                rows.append([bits, "Reserved", "", "", "", ""])
                continue
            reset = field.get_property("reset")
            if isinstance(reset, int):
                reset = hx(reset, (field.width + 3) // 4)
            elif reset is not None:
                reset = reset.get_path()            # reset given by a reference to another node
            name, desc = prop_text(field, "name"), prop_text(field, "desc")
            text = desc if name == desc else " ".join(t for t in (name, desc) if t)
            text = escape(text)
            encode = field.get_property("encode")
            if encode:
                values = escape(", ".join("%s = %s" % (hx(m.value), m.name) for m in encode))
                text = text + "<br/>" + values if text else values
            rows.append([bits, Paragraph(escape(field.inst_name), self.cell),
                         field.get_property("sw").name, field.get_property("hw").name,
                         reset or "", Paragraph(text, self.cell)])
        return self.table(rows, [0.7 * inch, 1.5 * inch, 0.75 * inch, 0.75 * inch, 0.9 * inch, None])
