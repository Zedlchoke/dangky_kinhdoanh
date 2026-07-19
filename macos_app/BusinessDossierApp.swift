import Cocoa
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var webView: WKWebView!
    var server: Process?

    let projectPath = "/Users/hoangminhlong/Downloads/xuly_dangky_doanhnghiep"
    let pythonPath = "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
    let port = "8790"

    func applicationDidFinishLaunching(_ notification: Notification) {
        startServer()

        let config = WKWebViewConfiguration()
        webView = WKWebView(frame: .zero, configuration: config)
        webView.setValue(false, forKey: "drawsBackground")

        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1320, height: 860),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Trợ lý hồ sơ đăng ký doanh nghiệp"
        window.center()
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
            self.loadApp()
        }
    }

    func startServer() {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = ["run_app.py", port]
        process.currentDirectoryURL = URL(fileURLWithPath: projectPath)
        process.standardOutput = Pipe()
        process.standardError = Pipe()
        do {
            try process.run()
            server = process
        } catch {
            showError("Không chạy được server local: \(error.localizedDescription)")
        }
    }

    func loadApp() {
        if let url = URL(string: "http://127.0.0.1:\(port)/") {
            webView.load(URLRequest(url: url))
        }
    }

    func showError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Không mở được ứng dụng"
        alert.informativeText = message
        alert.alertStyle = .critical
        alert.runModal()
    }

    func applicationWillTerminate(_ notification: Notification) {
        server?.terminate()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.activate(ignoringOtherApps: true)
app.run()
