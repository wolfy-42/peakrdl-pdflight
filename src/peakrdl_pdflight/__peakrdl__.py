#--------------------------------------------------------------------------------------------------
#
# SPDX-License-Identifier: Apache-2.0 OR MIT
#
# Project      : FPGA Project Template
# Author       : DV
# Created      : 2026-11-02
#--------------------------------------------------------------------------------------------------
# Description  : PeakRDL plugin descriptor: adds the subcommand "peakrdl pdflight" with its
#                options and hands the compiled register map to PdfExporter.
# Updated      : yyyy-mm-dd / author - comments
#--------------------------------------------------------------------------------------------------

from peakrdl.plugins.exporter import ExporterSubcommandPlugin

from .exporter import PdfExporter


class Exporter(ExporterSubcommandPlugin):
    short_desc = "Write the register map as a PDF document"

    def add_exporter_arguments(self, arg_group):
        arg_group.add_argument("--title", default=None,
                               help="document title (default: the top addrmap name, else its desc)")
        arg_group.add_argument("--page-size", choices=["letter", "a4"], default="letter",
                               help="page size (default: letter)")

    def do_export(self, top_node, options):
        PdfExporter().export(top_node, options.output, title=options.title,
                             page_size=options.page_size)
