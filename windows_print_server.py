import base64
import io
import json
import logging
import re
import socket
import sys
import threading
import time
import traceback

import qrcode
import win32print

from PIL import Image


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_PRINTER_NAME = "TAJO POS"

HOST = "0.0.0.0"

PORT = 9101

AUX_PORTS = [9300]

BUFFER_SIZE = 16384

MAX_DATA_SIZE = 20 * 1024 * 1024

SOCKET_TIMEOUT = 30

DEFAULT_PAPER_WIDTH_MM = 80

DEFAULT_PRINTABLE_WIDTH = 576

PRINT_SERVER_NAME = "Main POS Printer Server"

# Standard character width for 80mm thermal printers.
# 48 is suitable for most 80mm ESC/POS printers.
DEFAULT_CHARACTER_WIDTH = 48


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(

    level=logging.INFO,

    format=(
        "%(asctime)s - "
        "%(levelname)s - "
        "%(message)s"
    ),

    handlers=[

        logging.FileHandler(
            "print_server.log",
            encoding="utf-8",
        ),

        logging.StreamHandler(
            sys.stdout
        ),

    ],
)


# ============================================================
# PRINT SERVER
# ============================================================

class PrintServer:

    def __init__(
        self,
        host=HOST,
        port=PORT,
        server_name=PRINT_SERVER_NAME,
    ):

        self.host = host
        self.port = port
        self.server_name = server_name

        self.default_printer = DEFAULT_PRINTER_NAME

        self.running = False

        self.socket = None
        self.aux_sockets = []

        self.available_printers = (
            self.get_available_printers()
        )

    # ========================================================
    # WINDOWS PRINTERS
    # ========================================================

    def get_available_printers(self):

        try:

            printers = win32print.EnumPrinters(

                win32print.PRINTER_ENUM_LOCAL

            )

            return [

                p[2]

                for p in printers

            ]

        except Exception as e:

            logging.error(
                "Error getting printers: %s",
                e,
            )

            return []

    # ========================================================
    # SELECT PRINTER
    # ========================================================

    def get_printer(
        self,
        requested_name=None,
    ):

        self.available_printers = (
            self.get_available_printers()
        )

        if not self.available_printers:

            logging.error(
                "No printers available."
            )

            return None

        # ----------------------------------------------------
        # Exact match
        # ----------------------------------------------------

        if requested_name:

            if requested_name in (
                self.available_printers
            ):

                logging.info(
                    "Using requested printer: %s",
                    requested_name,
                )

                return requested_name

            # ------------------------------------------------
            # Case-insensitive match
            # ------------------------------------------------

            for printer in (
                self.available_printers
            ):

                if printer.lower() == (
                    requested_name.lower()
                ):

                    logging.info(
                        "Using case-insensitive match: %s",
                        printer,
                    )

                    return printer

            # ------------------------------------------------
            # Similar match
            # ------------------------------------------------

            for printer in (
                self.available_printers
            ):

                if (

                    requested_name.lower()
                    in printer.lower()

                ) or (

                    printer.lower()
                    in requested_name.lower()

                ):

                    logging.warning(

                        "Using similar printer '%s' "
                        "for requested '%s'",

                        printer,

                        requested_name,

                    )

                    return printer

        # ----------------------------------------------------
        # Default printer
        # ----------------------------------------------------

        if self.default_printer in (
            self.available_printers
        ):

            logging.info(
                "Using default printer: %s",
                self.default_printer,
            )

            return self.default_printer

        # ----------------------------------------------------
        # First available printer
        # ----------------------------------------------------

        logging.warning(

            "Configured default printer not found. "
            "Using first available printer: %s",

            self.available_printers[0],

        )

        return self.available_printers[0]

    # ========================================================
    # START
    # ========================================================

    def start(self):

        try:

            self.socket = socket.socket(

                socket.AF_INET,

                socket.SOCK_STREAM,

            )

            self.socket.setsockopt(

                socket.SOL_SOCKET,

                socket.SO_REUSEADDR,

                1,

            )

            try:
                self.socket.bind(
                    (
                        self.host,
                        self.port,
                    )
                )
            except (PermissionError, OSError) as bind_err:
                logging.warning(
                    "Could not bind to %s:%s (%s). Attempting alternative ports...",
                    self.host,
                    self.port,
                    bind_err,
                )
                fallback_ports = [9300, 9600, 9700, 9800, 8900]
                bound = False
                for alt_port in fallback_ports:
                    if alt_port == self.port:
                        continue
                    try:
                        self.socket.close()
                        self.socket = socket.socket(
                            socket.AF_INET,
                            socket.SOCK_STREAM,
                        )
                        self.socket.setsockopt(
                            socket.SOL_SOCKET,
                            socket.SO_REUSEADDR,
                            1,
                        )
                        self.socket.bind((self.host, alt_port))
                        self.port = alt_port
                        bound = True
                        logging.info("Successfully bound to fallback port: %s", self.port)
                        break
                    except Exception:
                        continue
                if not bound:
                    raise

            self.socket.listen(
                10
            )

            self.running = True

            logging.info(
                "================================================"
            )

            logging.info(
                "Clarity Retail Windows Print Server"
            )

            logging.info(
                "Server name: %s",
                self.server_name,
            )

            logging.info(
                "Listening on: %s:%s",
                self.host,
                self.port,
            )

            logging.info(
                "Default printer: %s",
                self.default_printer,
            )

            logging.info(
                "Available printers: %s",
                self.available_printers,
            )

            logging.info(
                "================================================"
            )

            logging.info(
                "Waiting for connections..."
            )

            # Start auxiliary listener threads on other ports (e.g. 9300) so connections to either port succeed
            for aux_p in AUX_PORTS:
                if aux_p != self.port:
                    threading.Thread(
                        target=self._run_aux_listener,
                        args=(aux_p,),
                        daemon=True
                    ).start()

            while self.running:

                try:

                    client_socket, address = (
                        self.socket.accept()
                    )

                    logging.info(
                        "Connection from %s",
                        address,
                    )

                    thread = threading.Thread(

                        target=self.handle_client,

                        args=(
                            client_socket,
                            address,
                        ),

                        daemon=True,

                    )

                    thread.start()

                except OSError as e:

                    if self.running:

                        logging.error(
                            "Accept error: %s",
                            e,
                        )

        except Exception as e:

            logging.error(
                "Failed to start server: %s",
                e,
            )

            logging.error(
                traceback.format_exc()
            )

            self.stop()

    # ========================================================
    # CLIENT HANDLER
    # ========================================================

    def handle_client(
        self,
        client_socket,
        address,
    ):

        try:

            client_socket.settimeout(
                SOCKET_TIMEOUT
            )

            data = bytearray()

            # ------------------------------------------------
            # Receive request
            # ------------------------------------------------

            while len(data) < MAX_DATA_SIZE:

                try:

                    chunk = client_socket.recv(
                        BUFFER_SIZE
                    )

                    if not chunk:

                        break

                    data.extend(
                        chunk
                    )

                except socket.timeout:

                    logging.warning(
                        "Socket timeout from %s",
                        address,
                    )

                    break

            if not data:

                logging.warning(
                    "No data received from %s",
                    address,
                )

                return

            if len(data) >= MAX_DATA_SIZE:

                logging.error(
                    "Request exceeded maximum size."
                )

                self.send_response(

                    client_socket,

                    {
                        "status": "error",

                        "message": (
                            "Print request is too large."
                        ),
                    },

                )

                return

            logging.info(

                "Received %s bytes from %s",

                len(data),

                address,

            )

            # ------------------------------------------------
            # Decode JSON
            # ------------------------------------------------

            try:

                decoded = data.decode(
                    "utf-8"
                )

                print_job = json.loads(
                    decoded
                )

            except UnicodeDecodeError:

                logging.error(
                    "Request was not valid UTF-8."
                )

                self.send_response(

                    client_socket,

                    {
                        "status": "error",

                        "message": (
                            "Request is not valid UTF-8."
                        ),
                    },

                )

                return

            except json.JSONDecodeError as e:

                logging.error(
                    "Invalid JSON: %s",
                    e,
                )

                self.send_response(

                    client_socket,

                    {
                        "status": "error",

                        "message": (
                            f"Invalid JSON: {e}"
                        ),
                    },

                )

                return

            # ------------------------------------------------
            # Validate object
            # ------------------------------------------------

            if not isinstance(
                print_job,
                dict,
            ):

                self.send_response(

                    client_socket,

                    {
                        "status": "error",

                        "message": (
                            "Print request must be a JSON object."
                        ),
                    },

                )

                return

            logging.info(
                "Print type: %s",
                print_job.get(
                    "type",
                    "unknown",
                ),
            )

            logging.info(
                "Requested printer: %s",
                print_job.get(
                    "printer_name",
                    "default",
                ),
            )

            # ------------------------------------------------
            # Process
            # ------------------------------------------------

            result = self.process_print_job(
                print_job
            )

            # ------------------------------------------------
            # Response
            # ------------------------------------------------

            self.send_response(
                client_socket,
                result,
            )

            logging.info(
                "Response sent: %s",
                result.get(
                    "status"
                ),
            )

        except ConnectionResetError:

            logging.warning(
                "Connection reset by %s",
                address,
            )

        except socket.timeout:

            logging.warning(
                "Socket timeout from %s",
                address,
            )

        except Exception as e:

            logging.error(
                "Error handling client: %s",
                e,
            )

            logging.error(
                traceback.format_exc()
            )

            try:

                self.send_response(

                    client_socket,

                    {
                        "status": "error",

                        "message": str(e),

                    },

                )

            except Exception:

                pass

        finally:

            try:

                client_socket.close()

            except Exception:

                pass

    # ========================================================
    # SEND RESPONSE
    # ========================================================

    def send_response(
        self,
        client_socket,
        result,
    ):

        try:

            response = json.dumps(
                result,
                ensure_ascii=False,
            ).encode(
                "utf-8"
            )

            client_socket.sendall(
                response
            )

        except Exception as e:

            logging.error(
                "Failed to send response: %s",
                e,
            )

    # ========================================================
    # PROCESS PRINT JOB
    # ========================================================

    def process_print_job(
        self,
        print_job,
    ):

        try:

            print_type = print_job.get(
                "type",
                "text",
            )

            requested_printer = (
                print_job.get(
                    "printer_name"
                )
            )

            printer_name = self.get_printer(
                requested_printer
            )

            if not printer_name:

                return {

                    "status": "error",

                    "message": (
                        "No Windows printer is available."
                    ),

                }

            # ------------------------------------------------
            # GENERIC DOCUMENT
            # ------------------------------------------------

            if print_type == "document":

                return self.print_document(
                    print_job,
                    printer_name,
                )

            # ------------------------------------------------
            # LEGACY
            # ------------------------------------------------

            elif print_type == "full_receipt":

                return self.print_full_receipt(
                    print_job,
                    printer_name,
                )

            elif print_type == "text":

                return self.print_text(
                    print_job,
                    printer_name,
                )

            elif print_type == "qr_only":

                return self.print_qr_only(
                    print_job,
                    printer_name,
                )

            else:

                return {

                    "status": "error",

                    "message": (
                        f"Unknown print type: {print_type}"
                    ),

                }

        except Exception as e:

            logging.error(
                "Error processing print job: %s",
                e,
            )

            logging.error(
                traceback.format_exc()
            )

            return {

                "status": "error",

                "message": str(e),

            }

    # ========================================================
    # GENERIC DOCUMENT
    # ========================================================

    def print_document(
        self,
        data,
        printer_name,
    ):

        document = data.get(
            "document"
        )

        if not isinstance(
            document,
            dict,
        ):

            return {

                "status": "error",

                "message": (
                    "Missing or invalid document."
                ),

            }

        if document.get(
            "type"
        ) != "document":

            return {

                "status": "error",

                "message": (
                    "Document type must be 'document'."
                ),

            }

        content = document.get(
            "content"
        )

        if not isinstance(
            content,
            list,
        ):

            return {

                "status": "error",

                "message": (
                    "Document content must be a list."
                ),

            }

        paper = document.get(
            "paper",
            {},
        )

        if not isinstance(
            paper,
            dict,
        ):

            paper = {}

        copies = self.safe_int(
            paper.get(
                "copies",
                1,
            ),
            1,
        )

        copies = max(
            1,
            min(
                copies,
                10,
            ),
        )

        cut = bool(
            paper.get(
                "cut",
                True,
            )
        )

        logging.info(
            "Printing dynamic document with %s elements",
            len(content),
        )

        logging.info(
            "Copies: %s | Cut: %s",
            copies,
            cut,
        )

        try:

            for copy_number in range(
                copies
            ):

                commands = bytearray()

                # ------------------------------------------------
                # Initialize printer
                # ------------------------------------------------

                commands += b"\x1b\x40"

                # ------------------------------------------------
                # Render elements
                # ------------------------------------------------

                for index, element in enumerate(
                    content
                ):

                    if not isinstance(
                        element,
                        dict,
                    ):

                        logging.warning(
                            "Skipping invalid element %s",
                            index,
                        )

                        continue

                    element_type = element.get(
                        "type"
                    )

                    try:

                        rendered = (
                            self.render_element(
                                element
                            )
                        )

                        if rendered:

                            commands += rendered

                    except Exception as e:

                        logging.error(

                            "Error rendering element "
                            "%s (%s): %s",

                            index,

                            element_type,

                            e,

                        )

                        logging.error(
                            traceback.format_exc()
                        )

                        return {

                            "status": "error",

                            "message": (
                                f"Failed to render "
                                f"element {index}: "
                                f"{e}"
                            ),

                        }

                # ------------------------------------------------
                # Feed
                # ------------------------------------------------

                commands += b"\n\n\n"

                # ------------------------------------------------
                # Cut
                # ------------------------------------------------

                if cut:

                    commands += b"\x1d\x56\x00"

                # ------------------------------------------------
                # Send
                # ------------------------------------------------

                self.send_to_printer(

                    bytes(commands),

                    printer_name,

                )

                logging.info(

                    "Document copy %s/%s "
                    "printed on %s",

                    copy_number + 1,

                    copies,

                    printer_name,

                )

            return {

                "status": "success",

                "message": (
                    "Document printed successfully "
                    f"on {printer_name}"
                ),

                "printer": printer_name,

                "copies": copies,

            }

        except Exception as e:

            logging.error(
                "Document printing failed: %s",
                e,
            )

            logging.error(
                traceback.format_exc()
            )

            return {

                "status": "error",

                "message": str(e),

                "printer": printer_name,

            }

    # ========================================================
    # ELEMENT RENDERER
    # ========================================================

    def render_element(
        self,
        element,
    ):

        element_type = element.get(
            "type"
        )

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        if element_type == "text":

            return self.render_text(
                element
            )

        # ----------------------------------------------------
        # DIVIDER
        # ----------------------------------------------------

        if element_type == "divider":

            return self.render_divider(
                element
            )

        # ----------------------------------------------------
        # SPACE
        # ----------------------------------------------------

        if element_type == "space":

            return self.render_space(
                element
            )

        # ----------------------------------------------------
        # LOGO / IMAGE
        # ----------------------------------------------------

        if element_type == "logo":

            return self.render_logo(
                element
            )

        if element_type == "image":

            return self.render_logo(
                element
            )

        # ----------------------------------------------------
        # QR
        # ----------------------------------------------------

        if element_type == "qr":

            return self.render_qr(
                element
            )

        # ----------------------------------------------------
        # BARCODE
        # ----------------------------------------------------

        if element_type == "barcode":

            return self.render_barcode(
                element
            )

        # ----------------------------------------------------
        # COLUMNS
        # ----------------------------------------------------

        if element_type == "columns":

            return self.render_columns(
                element
            )

        # ----------------------------------------------------
        # ROW
        #
        # THIS IS THE IMPORTANT ADDITION.
        #
        # Your Django test_printer() sends:
        #
        # {
        #     "type": "row",
        #     "columns": [...]
        # }
        #
        # ----------------------------------------------------

        if element_type == "row":

            return self.render_row(
                element
            )

        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        if element_type == "table":

            return self.render_table(
                element
            )

        if element_type == "items":

            return self.render_table(
                element
            )

        # ----------------------------------------------------
        # CUT
        # ----------------------------------------------------

        if element_type == "cut":

            return b"\x1d\x56\x00"

        # ----------------------------------------------------
        # UNKNOWN
        # ----------------------------------------------------

        logging.warning(
            "Unknown document element: %s",
            element_type,
        )

        return b""

    # ========================================================
    # TEXT
    # ========================================================

    def render_text(
        self,
        element,
    ):

        text = str(
            element.get(
                "text",
                "",
            )
        )

        align = str(
            element.get(
                "align",
                "left",
            )
        ).lower()

        bold = bool(
            element.get(
                "bold",
                False,
            )
        )

        underline = bool(
            element.get(
                "underline",
                False,
            )
        )

        size = self.safe_int(
            element.get(
                "size",
                1,
            ),
            1,
        )

        size = max(
            1,
            min(
                size,
                8,
            ),
        )

        commands = bytearray()

        # ----------------------------------------------------
        # Alignment
        # ----------------------------------------------------

        commands += self.get_alignment_command(
            align
        )

        # ----------------------------------------------------
        # Bold
        # ----------------------------------------------------

        commands += (

            b"\x1b\x45\x01"

            if bold

            else b"\x1b\x45\x00"

        )

        # ----------------------------------------------------
        # Underline
        # ----------------------------------------------------

        commands += (

            b"\x1b\x2d\x01"

            if underline

            else b"\x1b\x2d\x00"

        )

        # ----------------------------------------------------
        # Character size
        # ----------------------------------------------------

        size_value = (
            (size - 1)
            << 4
        ) | (
            size - 1
        )

        commands += bytes(
            [
                0x1D,
                0x21,
                size_value,
            ]
        )

        # ----------------------------------------------------
        # Text
        # ----------------------------------------------------

        lines = text.split(
            "\n"
        )

        for line in lines:

            commands += line.encode(
                "utf-8",
                errors="ignore",
            )

            commands += b"\n"

        # ----------------------------------------------------
        # Reset formatting
        # ----------------------------------------------------

        commands += b"\x1b\x45\x00"

        commands += b"\x1b\x2d\x00"

        commands += b"\x1d\x21\x00"

        return bytes(
            commands
        )

    # ========================================================
    # DIVIDER
    # ========================================================

    def render_divider(
        self,
        element,
    ):

        character = str(
            element.get(
                "character",
                "-",
            )
        )

        if not character:

            character = "-"

        character = character[0]

        width = self.safe_int(
            element.get(
                "width",
                DEFAULT_CHARACTER_WIDTH,
            ),
            DEFAULT_CHARACTER_WIDTH,
        )

        width = max(
            1,
            min(
                width,
                100,
            ),
        )

        align = element.get(
            "align",
            "left",
        )

        return self.render_text({

            "type": "text",

            "text": (
                character * width
            ),

            "align": align,

        })

    # ========================================================
    # SPACE
    # ========================================================

    def render_space(
        self,
        element,
    ):

        lines = self.safe_int(
            element.get(
                "lines",
                1,
            ),
            1,
        )

        lines = max(
            1,
            min(
                lines,
                20,
            ),
        )

        return (
            b"\n" * lines
        )

    # ========================================================
    # LOGO / IMAGE
    # ========================================================

    def render_logo(
        self,
        element,
    ):

        logo_data = element.get(
            "data"
        )

        if not logo_data:

            return b""

        try:

            logo_data = str(
                logo_data
            ).strip()

            # ------------------------------------------------
            # Support data URL
            # ------------------------------------------------

            if "," in logo_data:

                possible_header, possible_data = (
                    logo_data.split(
                        ",",
                        1,
                    )
                )

                if (
                    "base64"
                    in possible_header.lower()
                ):

                    logo_data = possible_data

            logo_data = re.sub(
                r"\s+",
                "",
                logo_data,
            )

            logo_bytes = base64.b64decode(
                logo_data
            )

            raw_image = Image.open(
                io.BytesIO(
                    logo_bytes
                )
            )

            # ------------------------------------------------
            # Handle transparency (RGBA / LA / P with alpha)
            # Flatten onto clean white background
            # ------------------------------------------------
            if raw_image.mode in ("RGBA", "LA") or (raw_image.mode == "P" and "transparency" in raw_image.info):
                rgba = raw_image.convert("RGBA")
                white_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                white_bg.paste(rgba, mask=rgba.split()[3])
                image = white_bg.convert("L")
            else:
                image = raw_image.convert("L")

            # ------------------------------------------------
            # Crop whitespace (bounding box of non-white content)
            # ------------------------------------------------
            content_mask = image.point(lambda p: 255 if p < 240 else 0)
            bbox = content_mask.getbbox()

            if bbox:
                image = image.crop(
                    bbox
                )

            target_width = self.safe_int(
                element.get(
                    "width",
                    300,
                ),
                300,
            )

            target_width = max(
                50,
                min(
                    target_width,
                    DEFAULT_PRINTABLE_WIDTH,
                ),
            )

            # ------------------------------------------------
            # Preserve aspect ratio.
            # This prevents the logo from stretching.
            # ------------------------------------------------
            image = self.resize_preserve_ratio(
                image,
                target_width,
            )

            # High quality binarization for thermal printer
            image = image.convert("1")

            align = element.get(
                "align",
                "center",
            )

            commands = bytearray()

            commands += (
                self.get_alignment_command(
                    align
                )
            )

            commands += self.image_to_escpos(
                image
            )

            commands += b"\n"

            return bytes(
                commands
            )

        except Exception as e:

            logging.error(
                "Logo rendering failed: %s",
                e,
            )

            return b""

    # ========================================================
    # QR
    # ========================================================

    def render_qr(
        self,
        element,
    ):

        qr_data = str(
            element.get(
                "data",
                "",
            )
        )

        if not qr_data:

            return b""

        align = element.get(
            "align",
            "center",
        )

        box_size = self.safe_int(
            element.get(
                "size",
                5,
            ),
            5,
        )

        box_size = max(
            2,
            min(
                box_size,
                12,
            ),
        )

        border = self.safe_int(
            element.get(
                "border",
                2,
            ),
            2,
        )

        border = max(
            0,
            min(
                border,
                10,
            ),
        )

        label = element.get(
            "label"
        )

        try:

            qr = qrcode.QRCode(

                version=None,

                error_correction=(
                    qrcode.constants
                    .ERROR_CORRECT_M
                ),

                box_size=box_size,

                border=border,

            )

            qr.add_data(
                qr_data
            )

            qr.make(
                fit=True
            )

            image = qr.make_image(
                fill_color="black",
                back_color="white",
            ).convert(
                "1"
            )

            commands = bytearray()

            commands += (
                self.get_alignment_command(
                    align
                )
            )

            if label:

                commands += (
                    str(label)
                    .encode(
                        "utf-8",
                        errors="ignore",
                    )
                )

                commands += b"\n"

            commands += self.image_to_escpos(
                image
            )

            commands += b"\n"

            return bytes(
                commands
            )

        except Exception as e:

            logging.error(
                "QR rendering failed: %s",
                e,
            )

            return b""

    # ========================================================
    # BARCODE
    # ========================================================

    def render_barcode(
        self,
        element,
    ):

        data = str(
            element.get(
                "data",
                "",
            )
        )

        if not data:

            return b""

        align = element.get(
            "align",
            "center",
        )

        height = self.safe_int(
            element.get(
                "height",
                60,
            ),
            60,
        )

        width = self.safe_int(
            element.get(
                "width",
                2,
            ),
            2,
        )

        width = max(
            2,
            min(
                width,
                6,
            ),
        )

        height = max(
            20,
            min(
                height,
                255,
            ),
        )

        commands = bytearray()

        commands += (
            self.get_alignment_command(
                align
            )
        )

        # HRI below barcode
        commands += b"\x1d\x48\x02"

        # Barcode height
        commands += bytes(
            [
                0x1D,
                0x68,
                height,
            ]
        )

        # Module width
        commands += bytes(
            [
                0x1D,
                0x77,
                width,
            ]
        )

        barcode_data = (
            b"\x1d\x6b\x49"
            + bytes([len(data) + 2])
            + b"\x7b\x42"
            + data.encode(
                "ascii",
                errors="ignore",
            )
            + b"\n"
        )

        commands += barcode_data

        return bytes(
            commands
        )

    # ========================================================
    # COLUMNS
    # ========================================================

    def render_columns(
        self,
        element,
    ):

        columns = element.get(
            "columns",
            [],
        )

        if not isinstance(
            columns,
            list,
        ):

            return b""

        commands = bytearray()

        for column in columns:

            if not isinstance(
                column,
                dict,
            ):

                continue

            text = " ".join(str(
                column.get(
                    "text",
                    "",
                )
            ).split())

            align = column.get(
                "align",
                "left",
            )

            width = self.safe_int(
                column.get(
                    "width",
                    DEFAULT_CHARACTER_WIDTH,
                ),
                DEFAULT_CHARACTER_WIDTH,
            )

            width = max(
                1,
                min(
                    width,
                    100,
                ),
            )

            if len(text) > width:
                text = text[:width]

            if align == "right":

                text = text.rjust(
                    width
                )

            elif align == "center":

                text = text.center(
                    width
                )

            else:

                text = text.ljust(
                    width
                )

            commands += text.encode(
                "utf-8",
                errors="ignore",
            )

        commands += b"\n"

        return bytes(
            commands
        )

    # ========================================================
    # ROW
    #
    # Supports the format used by your Django test_printer():
    #
    # {
    #     "type": "row",
    #     "columns": [
    #         {
    #             "text": "Item",
    #             "align": "left",
    #             "bold": True
    #         },
    #         ...
    #     ]
    # }
    #
    # ========================================================

    def render_row(
        self,
        element,
    ):

        columns = element.get(
            "columns",
            [],
        )

        if not isinstance(
            columns,
            list,
        ):

            logging.warning(
                "Row columns must be a list."
            )

            return b""

        if not columns:

            return b"\n"

        # ----------------------------------------------------
        # Determine available character width.
        # ----------------------------------------------------

        total_width = self.safe_int(
            element.get(
                "character_width",
                DEFAULT_CHARACTER_WIDTH,
            ),
            DEFAULT_CHARACTER_WIDTH,
        )

        total_width = max(
            20,
            min(
                total_width,
                100,
            ),
        )

        # ----------------------------------------------------
        # If explicit widths are supplied, use them.
        #
        # Example:
        #
        # width: 24
        # width: 8
        # width: 16
        #
        # Otherwise calculate widths automatically.
        # ----------------------------------------------------

        explicit_widths = []

        has_explicit_width = False

        for column in columns:

            if not isinstance(
                column,
                dict,
            ):

                explicit_widths.append(
                    1
                )

                continue

            if "width" in column:

                width = self.safe_int(
                    column.get(
                        "width"
                    ),
                    1,
                )

                width = max(
                    1,
                    width,
                )

                explicit_widths.append(
                    width
                )

                has_explicit_width = True

            else:

                explicit_widths.append(
                    0
                )

        # ----------------------------------------------------
        # Automatic width calculation.
        #
        # This is mainly useful for your test printer where
        # widths are not specified.
        # ----------------------------------------------------

        if not has_explicit_width:

            count = len(
                columns
            )

            if count == 1:

                widths = [
                    total_width
                ]

            elif count == 2:

                col2 = min(14, max(8, total_width // 3))
                widths = [
                    total_width - col2,
                    col2,
                ]

            elif count == 3:

                # Good default for:
                #
                # Item | Qty | Amount
                #

                first = max(
                    1,
                    total_width - 18 - 12,
                )

                widths = [
                    first,
                    18,
                    12,
                ]

            else:

                base_width = (
                    total_width
                    // count
                )

                widths = [
                    base_width
                    for _ in columns
                ]

                remainder = (
                    total_width
                    - sum(widths)
                )

                if remainder > 0:

                    widths[-1] += remainder

        else:

            widths = []

            remaining_width = total_width

            unspecified_indexes = []

            for index, column in enumerate(
                columns
            ):

                if not isinstance(
                    column,
                    dict,
                ):

                    unspecified_indexes.append(
                        index
                    )

                    widths.append(
                        0
                    )

                    continue

                width = self.safe_int(
                    column.get(
                        "width",
                        0,
                    ),
                    0,
                )

                if width > 0:

                    widths.append(
                        width
                    )

                    remaining_width -= width

                else:

                    widths.append(
                        0
                    )

                    unspecified_indexes.append(
                        index
                    )

            if unspecified_indexes:

                remaining_width = max(
                    len(unspecified_indexes),
                    remaining_width,
                )

                each = max(
                    1,
                    remaining_width
                    // len(
                        unspecified_indexes
                    ),
                )

                for index in (
                    unspecified_indexes
                ):

                    widths[index] = each

                # Correct rounding/remainder.
                difference = (
                    total_width
                    - sum(widths)
                )

                if difference > 0:

                    widths[-1] += difference

        # ----------------------------------------------------
        # Build line
        # ----------------------------------------------------

        commands = bytearray()

        for index, column in enumerate(
            columns
        ):

            if not isinstance(
                column,
                dict,
            ):

                continue

            text = str(
                column.get(
                    "text",
                    "",
                )
            )

            align = str(
                column.get(
                    "align",
                    "left",
                )
            ).lower()

            bold = bool(
                column.get(
                    "bold",
                    False,
                )
            )

            underline = bool(
                column.get(
                    "underline",
                    False,
                )
            )

            size = self.safe_int(
                column.get(
                    "size",
                    1,
                ),
                1,
            )

            size = max(
                1,
                min(
                    size,
                    8,
                ),
            )

            width = widths[index]

            # ------------------------------------------------
            # If text is too long, truncate it.
            # ------------------------------------------------

            if len(text) > width:

                text = text[:width]

            # ------------------------------------------------
            # Alignment.
            # ------------------------------------------------

            if align == "right":

                text = text.rjust(
                    width
                )

            elif align == "center":

                text = text.center(
                    width
                )

            else:

                text = text.ljust(
                    width
                )

            # ------------------------------------------------
            # Formatting.
            # ------------------------------------------------

            commands += (
                b"\x1b\x45\x01"
                if bold
                else b"\x1b\x45\x00"
            )

            commands += (
                b"\x1b\x2d\x01"
                if underline
                else b"\x1b\x2d\x00"
            )

            size_value = (
                (size - 1) << 4
            ) | (
                size - 1
            )

            commands += bytes(
                [
                    0x1D,
                    0x21,
                    size_value,
                ]
            )

            commands += text.encode(
                "utf-8",
                errors="ignore",
            )

            # ------------------------------------------------
            # Reset before next column.
            # ------------------------------------------------

            commands += b"\x1b\x45\x00"

            commands += b"\x1b\x2d\x00"

            commands += b"\x1d\x21\x00"

        commands += b"\n"

        return bytes(
            commands
        )

    # ========================================================
    # TABLE
    # ========================================================

    def render_table(
        self,
        element,
    ):

        columns = element.get(
            "columns",
            [],
        )

        rows = element.get(
            "rows",
            [],
        )

        if not isinstance(
            columns,
            list,
        ):

            return b""

        if not isinstance(
            rows,
            list,
        ):

            return b""

        commands = bytearray()

        total_width = self.safe_int(
            element.get(
                "character_width",
                DEFAULT_CHARACTER_WIDTH,
            ),
            DEFAULT_CHARACTER_WIDTH,
        )

        total_width = max(
            20,
            min(
                total_width,
                100,
            ),
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        header_parts = []

        for column in columns:

            if not isinstance(
                column,
                dict,
            ):

                continue

            width = self.safe_int(
                column.get(
                    "width",
                    10,
                ),
                10,
            )

            title = str(
                column.get(
                    "title",
                    column.get(
                        "key",
                        "",
                    ),
                )
            )

            align = column.get(
                "align",
                "left",
            )

            header_parts.append(

                self.fit_text(
                    title,
                    width,
                    align,
                )

            )

        commands += (
            "".join(
                header_parts
            )
            .encode(
                "utf-8",
                errors="ignore",
            )
        )

        commands += b"\n"

        # ----------------------------------------------------
        # Divider
        # ----------------------------------------------------

        commands += (
            b"-" * total_width
        )

        commands += b"\n"

        # ----------------------------------------------------
        # Rows
        # ----------------------------------------------------

        for row in rows:

            if not isinstance(
                row,
                dict,
            ):

                continue

            wrapped_values = []

            max_lines = 1

            for column in columns:

                key = column.get(
                    "key",
                    "",
                )

                width = self.safe_int(
                    column.get(
                        "width",
                        10,
                    ),
                    10,
                )

                value = str(
                    row.get(
                        key,
                        "",
                    )
                )

                wrapped = self.wrap_text(
                    value,
                    width,
                )

                wrapped_values.append(
                    (
                        wrapped,
                        column,
                    )
                )

                max_lines = max(
                    max_lines,
                    len(wrapped),
                )

            for line_index in range(
                max_lines
            ):

                line = ""

                for wrapped, column in (
                    wrapped_values
                ):

                    width = self.safe_int(
                        column.get(
                            "width",
                            10,
                        ),
                        10,
                    )

                    align = column.get(
                        "align",
                        "left",
                    )

                    if line_index < len(
                        wrapped
                    ):

                        value = wrapped[
                            line_index
                        ]

                    else:

                        value = ""

                    line += self.fit_text(
                        value,
                        width,
                        align,
                    )

                commands += line.encode(
                    "utf-8",
                    errors="ignore",
                )

                commands += b"\n"

        return bytes(
            commands
        )

    # ========================================================
    # TEXT HELPERS
    # ========================================================

    def fit_text(
        self,
        text,
        width,
        align="left",
    ):

        text = str(
            text
        )

        width = max(
            1,
            int(width),
        )

        if len(text) > width:

            text = text[
                :width
            ]

        if align == "right":

            return text.rjust(
                width
            )

        if align == "center":

            return text.center(
                width
            )

        return text.ljust(
            width
        )

    def wrap_text(
        self,
        text,
        width,
    ):

        text = str(
            text
        )

        width = max(
            1,
            int(width),
        )

        if not text:

            return [""]

        words = text.split(
            " "
        )

        lines = []

        current = ""

        for word in words:

            if len(word) > width:

                if current:

                    lines.append(
                        current
                    )

                    current = ""

                while len(word) > width:

                    lines.append(
                        word[:width]
                    )

                    word = word[
                        width:
                    ]

                current = word

            else:

                if not current:

                    current = word

                elif len(
                    current
                ) + 1 + len(
                    word
                ) <= width:

                    current += (
                        " "
                        + word
                    )

                else:

                    lines.append(
                        current
                    )

                    current = word

        if current:

            lines.append(
                current
            )

        return lines or [""]

    # ========================================================
    # ALIGNMENT
    # ========================================================

    def get_alignment_command(
        self,
        align,
    ):

        align = str(
            align
        ).lower()

        if align == "center":

            return b"\x1b\x61\x01"

        if align == "right":

            return b"\x1b\x61\x02"

        return b"\x1b\x61\x00"

    # ========================================================
    # INTEGER
    # ========================================================

    def safe_int(
        self,
        value,
        default,
    ):

        try:

            return int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return default

    # ========================================================
    # RESIZE
    # ========================================================

    def resize_preserve_ratio(
        self,
        image,
        target_width,
    ):

        if image.width <= 0:

            return image

        aspect_ratio = (
            image.height
            / image.width
        )

        target_height = max(

            1,

            round(
                target_width
                * aspect_ratio
            ),

        )

        return image.resize(

            (
                target_width,
                target_height,
            ),

            Image.Resampling.LANCZOS,

        )

    # ========================================================
    # IMAGE → ESC/POS
    # ========================================================

    def image_to_escpos(
        self,
        image,
    ):

        image = image.convert(
            "1"
        )

        width, height = (
            image.size
        )

        width_bytes = (
            width + 7
        ) // 8

        padded_width = (
            width_bytes * 8
        )

        if padded_width != width:

            padded = Image.new(

                "1",

                (
                    padded_width,
                    height,
                ),

                1,

            )

            padded.paste(
                image,
                (
                    0,
                    0,
                ),
            )

            image = padded

            width = padded_width

        data = bytearray()

        # ----------------------------------------------------
        # GS v 0 raster image
        # ----------------------------------------------------

        data += b"\x1d\x76\x30\x00"

        data += bytes([

            width_bytes & 0xff,

            (
                width_bytes >> 8
            ) & 0xff,

            height & 0xff,

            (
                height >> 8
            ) & 0xff,

        ])

        pixels = image.load()

        for y in range(
            height
        ):

            for x_byte in range(
                width_bytes
            ):

                byte = 0

                for bit in range(
                    8
                ):

                    x = (
                        x_byte * 8
                        + bit
                    )

                    if x < width:

                        if pixels[
                            x,
                            y,
                        ] == 0:

                            byte |= (
                                1
                                << (
                                    7 - bit
                                )
                            )

                data.append(
                    byte
                )

        return bytes(
            data
        )

    # ========================================================
    # LEGACY FULL RECEIPT
    # ========================================================

    def print_full_receipt(
        self,
        data,
        printer_name,
    ):

        try:

            commands = bytearray()

            commands += b"\x1b\x40"

            # ------------------------------------------------
            # Logo
            # ------------------------------------------------

            logo_data = data.get(
                "logo_data"
            )

            if logo_data:

                commands += (
                    self.render_logo({

                        "type": "logo",

                        "data": logo_data,

                        "width": 300,

                        "align": "center",

                    })
                )

            # ------------------------------------------------
            # Text 1
            # ------------------------------------------------

            text1 = data.get(

                "text1",

                (
                    "AVAIL TECHNOLOGIES\n"
                    "CLARITY RETAIL\n"
                    "PRINTER TEST"
                ),

            )

            commands += (
                self.render_text({

                    "type": "text",

                    "text": text1,

                    "align": "center",

                    "bold": True,

                })
            )

            # ------------------------------------------------
            # Small logo
            # ------------------------------------------------

            if logo_data:

                commands += (
                    self.render_logo({

                        "type": "logo",

                        "data": logo_data,

                        "width": 180,

                        "align": "center",

                    })
                )

            # ------------------------------------------------
            # Text 2
            # ------------------------------------------------

            text2 = data.get(
                "text2",
                "",
            )

            if text2:

                commands += (
                    self.render_text({

                        "type": "text",

                        "text": text2,

                        "align": "left",

                    })
                )

            # ------------------------------------------------
            # QR
            # ------------------------------------------------

            qr_data = data.get(
                "qr_data",
                "",
            )

            if qr_data:

                commands += (
                    self.render_qr({

                        "type": "qr",

                        "data": qr_data,

                        "label": (
                            "Scan to verify"
                        ),

                        "size": 5,

                        "align": "center",

                    })
                )

            # ------------------------------------------------
            # Footer
            # ------------------------------------------------

            footer = data.get(

                "footer",

                (
                    "Thank you for your business!\n"
                    "Powered by Clarity Retail"
                ),

            )

            commands += (
                self.render_text({

                    "type": "text",

                    "text": footer,

                    "align": "center",

                })
            )

            commands += b"\n\n\n"

            commands += b"\x1d\x56\x00"

            self.send_to_printer(

                bytes(commands),

                printer_name,

            )

            return {

                "status": "success",

                "message": (
                    "Receipt printed successfully "
                    f"on {printer_name}"
                ),

                "printer": printer_name,

            }

        except Exception as e:

            logging.error(
                "Legacy receipt error: %s",
                e,
            )

            raise

    # ========================================================
    # LEGACY TEXT
    # ========================================================

    def print_text(
        self,
        data,
        printer_name,
    ):

        text = data.get(
            "text",
            "",
        )

        commands = bytearray()

        commands += b"\x1b\x40"

        commands += (
            self.render_text({

                "type": "text",

                "text": text,

                "align": "left",

            })
        )

        commands += b"\n\n\n"

        commands += b"\x1d\x56\x00"

        self.send_to_printer(

            bytes(commands),

            printer_name,

        )

        return {

            "status": "success",

            "message": (
                f"Text printed successfully "
                f"on {printer_name}"
            ),

            "printer": printer_name,

        }

    # ========================================================
    # LEGACY QR
    # ========================================================

    def print_qr_only(
        self,
        data,
        printer_name,
    ):

        qr_data = data.get(
            "qr_data",
            "",
        )

        commands = bytearray()

        commands += b"\x1b\x40"

        if qr_data:

            commands += (
                self.render_qr({

                    "type": "qr",

                    "data": qr_data,

                    "size": 7,

                    "align": "center",

                })
            )

        commands += b"\n\n\n"

        commands += b"\x1d\x56\x00"

        self.send_to_printer(

            bytes(commands),

            printer_name,

        )

        return {

            "status": "success",

            "message": (
                f"QR code printed successfully "
                f"on {printer_name}"
            ),

            "printer": printer_name,

        }

    # ========================================================
    # SEND RAW DATA TO WINDOWS PRINTER
    # ========================================================

    def send_to_printer(
        self,
        commands,
        printer_name,
    ):

        hprinter = None

        try:

            logging.info(
                "Opening printer: %s",
                printer_name,
            )

            hprinter = (
                win32print.OpenPrinter(
                    printer_name
                )
            )

            win32print.StartDocPrinter(

                hprinter,

                1,

                (
                    "Clarity Retail Print",
                    None,
                    "RAW",
                ),

            )

            win32print.StartPagePrinter(
                hprinter
            )

            win32print.WritePrinter(

                hprinter,

                commands,

            )

            win32print.EndPagePrinter(
                hprinter
            )

            win32print.EndDocPrinter(
                hprinter
            )

            logging.info(

                "Print sent successfully "
                "to %s (%s bytes)",

                printer_name,

                len(commands),

            )

        except Exception as e:

            logging.error(
                "Printer error: %s",
                e,
            )

            logging.error(
                traceback.format_exc()
            )

            raise

        finally:

            if hprinter:

                try:

                    win32print.ClosePrinter(
                        hprinter
                    )

                except Exception:

                    pass

    def _run_aux_listener(self, port):
        try:
            aux_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            aux_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            aux_sock.bind((self.host, port))
            aux_sock.listen(10)
            self.aux_sockets.append(aux_sock)
            logging.info("Also listening on auxiliary port: %s:%s", self.host, port)
            while self.running:
                try:
                    client_socket, address = aux_sock.accept()
                    logging.info("Connection from %s (on aux port %s)", address, port)
                    threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    ).start()
                except OSError:
                    break
        except Exception as e:
            logging.warning("Could not bind auxiliary port %s: %s", port, e)

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self.running = False

        if self.socket:

            try:

                self.socket.close()

            except Exception:

                pass

        for aux_s in self.aux_sockets:
            try:
                aux_s.close()
            except Exception:
                pass
        self.aux_sockets.clear()

        logging.info(
            "Print server stopped."
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    server = None

    try:

        # ----------------------------------------------------
        # Detect Windows printers
        # ----------------------------------------------------

        printers = (
            win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL
            )
        )

        available = [

            p[2]

            for p in printers

        ]

        logging.info(
            "Available Windows printers: %s",
            available,
        )

        default_printer = (
            DEFAULT_PRINTER_NAME
        )

        # ----------------------------------------------------
        # Exact configured printer
        # ----------------------------------------------------

        if default_printer not in available:

            # ------------------------------------------------
            # Try common POS printer names
            # ------------------------------------------------

            for printer in available:

                printer_lower = (
                    printer.lower()
                )

                if (

                    "pos"
                    in printer_lower

                    or

                    "80c"
                    in printer_lower

                    or

                    "tajo"
                    in printer_lower

                    or

                    "xp-76"
                    in printer_lower

                ):

                    default_printer = (
                        printer
                    )

                    logging.info(

                        "Using detected POS "
                        "printer as default: %s",

                        printer,

                    )

                    break

            else:

                if available:

                    default_printer = (
                        available[0]
                    )

                    logging.warning(

                        "Configured default printer "
                        "not found. Using: %s",

                        default_printer,
                    )

        # ----------------------------------------------------
        # Parse CLI arguments if provided
        # ----------------------------------------------------
        server_host = HOST
        server_port = PORT
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                if arg.isdigit():
                    server_port = int(arg)
                elif arg.startswith("--port="):
                    server_port = int(arg.split("=", 1)[1])
                elif arg.startswith("--host="):
                    server_host = arg.split("=", 1)[1]
                elif arg.startswith("--printer="):
                    default_printer = arg.split("=", 1)[1]

        # ----------------------------------------------------
        # Create server
        # ----------------------------------------------------

        server = PrintServer(

            host=server_host,

            port=server_port,

        )

        server.default_printer = (
            default_printer
        )

        # ----------------------------------------------------
        # Startup information
        # ----------------------------------------------------

        logging.info(
            "================================================"
        )

        logging.info(
            "Clarity Retail Windows Print Server"
        )

        logging.info(
            "Server Name    : %s",
            server.server_name,
        )

        logging.info(
            "Default Printer: %s",
            server.default_printer,
        )

        logging.info(
            "Address        : %s:%s",
            server.host,
            server.port,
        )

        logging.info(
            "Available      : %s",
            server.get_available_printers(),
        )

        logging.info(
            "================================================"
        )

        # ----------------------------------------------------
        # Start
        # ----------------------------------------------------

        server.start()

    except KeyboardInterrupt:

        logging.info(
            "Shutting down..."
        )

        if server:

            server.stop()

    except Exception as e:

        logging.error(
            "Fatal error: %s",
            e,
        )

        logging.error(
            traceback.format_exc()
        )

        if server:

            server.stop()