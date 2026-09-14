"""Generate owned PDF test bytes without reportlab (not a PDF reader).

The committed sample is a deliberately simple PDF 1.4 with Helvetica text,
a text table, and an empty middle page. Encryption uses optional pypdf.
"""
from pathlib import Path


def sample_bytes():
    streams = [b'BT /F1 12 Tf 72 720 Td (Page One Alpha) Tj 0 -20 Td (Name    Value) Tj 0 -20 Td (alpha   1) Tj ET',
               b'', b'BT /F1 12 Tf 72 720 Td (Page Three Omega) Tj ET']
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [4 0 R 6 0 R 8 0 R] /Count 3 >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for index, stream in enumerate(streams):
        content_id = 5 + index * 2
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode())
        objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream')
    output = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(output)
    output.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        output.extend(f'{offset:010d} 00000 n \n'.encode())
    output.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(output)


if __name__ == '__main__':
    import pypdf
    root = Path(__file__).parent / 'source'
    root.mkdir(exist_ok=True)
    sample = root / 'sample.pdf'
    sample.write_bytes(sample_bytes())
    writer = pypdf.PdfWriter(clone_from=sample)
    writer.encrypt('fixture-password', algorithm='RC4-128')
    writer.write(root / 'sample-encrypted.pdf')
