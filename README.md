<!--------------------------------------------------------------------------------------------------

 SPDX-License-Identifier: Apache-2.0 OR MIT

 Project      : FPGA Project Template
 Author       : DV
 Created      : 2026-11-02
----------------------------------------------------------------------------------------------------
 Description  : Readme of peakrdl-pdflight.
 Updated      : yyyy-mm-dd / author - comments
--------------------------------------------------------------------------------------------------->

# peakrdl-pdflight

A [PeakRDL](https://github.com/SystemRDL/PeakRDL) exporter that writes a SystemRDL register map
as a PDF (with [reportlab](https://www.reportlab.com/)).

## Install

    pip install -e peakrdl-pdflight

## Use

    peakrdl pdflight <rdl files> -o map.pdf [--title TEXT] [--page-size letter|a4]

- `--title`: document title; default the top addrmap `name`, else its `desc`, else no title.
- `--page-size`: `letter` (default) or `a4`.

## Output

- Title page (title, top RDL file name, top name and desc, generation time), table of
  contents, PDF bookmarks. Footer: PeakRDL modules used and "Page N of M".
- One numbered section per block, memory and register (`1`, `1.x`, `1.x.y`, ...); heading
  `<num> <address> <instance name> Size: <size>`; blocks and memories show
  `<start> - <last>` instead of the address; the top has no address.
- Blocks: description and a table of their children, linked to the child sections.
- Memories: description and a table with width and number of entries.
- Registers: description, a bit drawing (32 bits per row, field names where they fit
  at 4 points or more, otherwise left out) and a field table
  (Bits, Name, SW access, HW access, Reset, Description; unused bits as Reserved rows).
- Every section links up to its parent and back to the table of contents.
- Every block below the top starts on a new page; numbered headings and table of contents
  entries are dark blue.
- Hex numbers in capitals; addresses zero-padded to the widest address.

## Repository

https://github.com/wolfy-42/peakrdl-pdflight (push / pull: `git@github.com:wolfy-42/peakrdl-pdflight.git`)

## License

Apache-2.0 OR MIT, see `LICENSE` and `LICENSE-APACHE`.
