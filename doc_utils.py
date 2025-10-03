import re
import subprocess
import logging

from typing import List, Optional

import matplotlib as mpl

class DocsHelper:
    @staticmethod
    def pretty_address(address: int, subtile_address: Optional[int] = None) -> str:
        """
        Format the address and subtile address (if applicable) into an nice string for the typst template
        """
        content = str(address).rjust(4, "-")
        if subtile_address != None:
            content += f"/{subtile_address}"
        return content
    
    @staticmethod
    def pretty_clock(clock: int) -> str:
        """
        Format the clock with engineering notation
        """
        if clock == 0:
            return "No Clock"
        else:
            formatter = mpl.ticker.EngFormatter(sep=" ")
            # [clock, SI suffix]
            hz_as_eng = formatter(clock).split(" ")

        if len(hz_as_eng) == 2:
            return f"{hz_as_eng[0]} {hz_as_eng[1]}Hz"
        elif len(hz_as_eng) == 1:
            return f"{hz_as_eng[0]} Hz"
        else:
            raise RuntimeError("unexpected amount of entries when formatting clock for datasheet")
    
    @staticmethod
    def format_authors(authors: str) -> str:
        """
        Format the authors properly

        Split the authors with a set of delimiters, then repackage as a typst array for the template
        """
        split_authors = re.split(r"[,|;|+]| and | & ", authors)
        formatted_authors = []
        for author in split_authors:
            stripped = author.strip()
            if stripped == "":
                continue

            # typst needs a trailing comma if len(array) == 1, so that it doesn't interpret it as an expression
            # https://typst.app/docs/reference/foundations/array/
            formatted_authors.append(f"\"{stripped}\",")
        return "".join(formatted_authors)
    
    @staticmethod
    def _escape_square_brackets(text: str) -> str:
        """
        Helper function to escape square brackets in strings
        """
        return text.replace("[", "\\[").replace("]", "\\]")
    
    @staticmethod
    def format_digital_pins(pins: dict) -> str:
        """
        Iterate through and create the digital pin table as a string
        """
        pin_table = ""
        for pin in pins:
            ui_text = DocsHelper._escape_square_brackets(pin["ui"])
            uo_text = DocsHelper._escape_square_brackets(pin["uo"])
            uio_text = DocsHelper._escape_square_brackets(pin["uio"])
            pin_table += f"[`{pin["pin_index"]}`], [{ui_text}], [{uo_text}], [{uio_text}],\n"

        return pin_table
    
    @staticmethod
    def format_analog_pins(pins: dict):
        """
        Iterate through and create the analog pin table as a string
        """
        pin_table = ""
        for pin in pins:
            desc_text = DocsHelper._escape_square_brackets(pin["desc"])
            pin_table += f"[`{pin["ua_index"]}`], [`{pin["analog_index"]}`], [{desc_text}],\n"
        return pin_table
    
    @staticmethod
    def get_docs_as_typst(path: str) -> subprocess.CompletedProcess:
        pandoc_command = ["pandoc", path, 
                              "--shift-heading-level-by=-1", "-f", "markdown-auto_identifiers", "-t", "typst", 
                              "--columns=120"]
        logging.info(pandoc_command)

        return subprocess.run(pandoc_command, capture_output=True)
    
    @staticmethod
    def get_project_type(language: str, is_wokwi: bool, is_analog: bool) -> str:
        if is_wokwi:
            return "Wokwi"
        elif is_analog:
            return "Analog"
        else:
            return "HDL"