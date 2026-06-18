import argparse
import os
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF is required. Install with: pip install PyMuPDF", file=sys.stderr)
    sys.exit(1)


def pdf_to_images(pdf_path, output_dir, dpi=200):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    print(f"Converting {pdf_path} ({doc.page_count} pages) → {output_dir}/")

    for i, page in enumerate(doc):
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        out_path = os.path.join(output_dir, f"page_{i + 1:04d}.png")
        pix.save(out_path)
        print(f"  [{i + 1}/{doc.page_count}] {out_path}")

    doc.close()
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Convert PDF pages to PNG images.")
    parser.add_argument("pdf", help="Path to the input PDF file")
    parser.add_argument("--output_dir", default="imgs", help="Output directory (default: imgs)")
    parser.add_argument("--dpi", type=int, default=200, help="Output image DPI (default: 200)")
    args = parser.parse_args()

    if not os.path.isfile(args.pdf):
        print(f"Error: file not found — {args.pdf}", file=sys.stderr)
        sys.exit(1)

    pdf_to_images(args.pdf, args.output_dir, args.dpi)


if __name__ == "__main__":
    main()
