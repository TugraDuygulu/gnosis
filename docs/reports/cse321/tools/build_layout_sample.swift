// macOS-only optional report QA helper; no application dependency.
// swift -module-cache-path /tmp/gnosis-swift-cache build_layout_sample.swift ROOT OUTPUT.pdf
import AppKit
import PDFKit
let args = CommandLine.arguments
precondition(args.count == 3, "Pass repository root and output PDF path")
let root = URL(fileURLWithPath: args[1])
let output = URL(fileURLWithPath: args[2])
var defaultBox = CGRect(x: 0, y: 0, width: 595.28, height: 841.89)
guard let pdf = CGContext(output as CFURL, mediaBox: &defaultBox, nil) else { fatalError("PDF output failed") }
func label(_ value: String, _ x: CGFloat, _ y: CGFloat, _ size: CGFloat = 11, mono: Bool = false) {
    let font = mono ? NSFont.monospacedSystemFont(ofSize: size, weight: .regular) : NSFont.systemFont(ofSize: size)
    (value as NSString).draw(at: NSPoint(x: x, y: y), withAttributes: [.font: font, .foregroundColor: NSColor.black])
}
func page(_ title: String, _ landscape: Bool, _ body: (CGFloat, CGFloat) -> Void) {
    let w: CGFloat = landscape ? 841.89 : 595.28
    let h: CGFloat = landscape ? 595.28 : 841.89
    var pageBox = CGRect(x: 0, y: 0, width: w, height: h)
    let pageData = NSData(bytes: &pageBox, length: MemoryLayout<CGRect>.size)
    pdf.beginPDFPage([kCGPDFContextMediaBox as String: pageData] as CFDictionary)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(cgContext: pdf, flipped: false)
    NSColor.white.setFill(); NSBezierPath(rect: NSRect(x: 0, y: 0, width: w, height: h)).fill()
    label("Gnosis report layout sample - NOT a final submission", 36, h-34, 12)
    label(title, 36, h-57, 11)
    body(w,h)
    label("A4; 36 pt margins. Inspect at 125% viewing. Final layout remains pending.", 36, 19, 9)
    NSGraphicsContext.restoreGraphicsState()
    pdf.endPDFPage()
}
for (name,title,landscape) in [
    ("architecture", "1. Component diagram - landscape A4", true),
    ("grading-classes", "2. Grading classes - portrait A4 full-figure fit", false),
    ("grade-workflow", "3. Sequence - portrait A4 full-figure fit (density probe)", false)
] {
    page(title, landscape) { w,h in
        let file = root.appendingPathComponent("docs/reports/cse321/diagrams/\(name).png")
        guard let image = NSImage(contentsOf: file) else { fatalError("Image missing: \(file.path)") }
        let area = NSRect(x: 36, y: 43, width: w-72, height: h-120)
        let scale = min(area.width/image.size.width, area.height/image.size.height)
        let size = NSSize(width: image.size.width*scale, height: image.size.height*scale)
        image.draw(in: NSRect(x: area.midX-size.width/2, y: area.midY-size.height/2, width: size.width, height: size.height))
    }
}
page("4. Query 1 - original SQL, 10 pt monospaced, landscape A4", true) { w,h in
    let text = try! String(contentsOf: root.appendingPathComponent("sql/01_student_assessment_grades.sql"), encoding: .utf8)
    for (index,line) in text.components(separatedBy: "\n").enumerated() {
        label(line, 36, h-86-CGFloat(index)*14, 10, mono: true)
    }
}
pdf.closePDF()
guard let document = PDFDocument(url: output) else { fatalError("PDF readback failed") }
precondition(document.pageCount == 4)
// 72 PDF points/inch * 1.25 = 90 dpi: actual 125% page raster.
for index in 0..<document.pageCount {
    let p = document.page(at:index)!
    let box = p.bounds(for: .mediaBox)
    let thumbnail = p.thumbnail(of: NSSize(width: box.width*1.25, height: box.height*1.25), for: .mediaBox)
    let bitmap = NSBitmapImageRep(data: thumbnail.tiffRepresentation!)!
    let imageURL = output.deletingLastPathComponent().appendingPathComponent("layout-page-\(index+1)-125.png")
    try! bitmap.representation(using: .png, properties: [:])!.write(to:imageURL)
}
print("Wrote four-page representative sample and four 125% page rasters: \(output.path)")
