// RefractionApp.swift — Main entry point for the Refraction macOS app.
// Launches the Python analysis server on appear and stops it on disappear.
// Title bar shows project filename.

import SwiftUI

@main
struct RefractionApp: App {

    @State private var appState = AppState()
    @State private var pythonServer = PythonServer()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)
                .environment(pythonServer)
                .onAppear {
                    pythonServer.start()
                    // Maximize the window on launch
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                        if let window = NSApplication.shared.mainWindow {
                            window.zoom(nil)
                        }
                    }
                }
                .onDisappear {
                    appState.saveProject()
                    pythonServer.stop()
                }
                .alert(
                    "Python Server Crashed",
                    isPresented: $pythonServer.showCrashAlert,
                    actions: {
                        Button("Restart Server") {
                            pythonServer.dismissCrashAlert()
                            pythonServer.stop()
                            pythonServer.start()
                        }
                        Button("Dismiss", role: .cancel) {
                            pythonServer.dismissCrashAlert()
                        }
                    },
                    message: {
                        Text(pythonServer.lastCrashMessage ?? "The analysis engine stopped unexpectedly.")
                    }
                )
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified(showsTitle: true))
        .defaultSize(width: 1200, height: 800)
        .commands {
            // File menu: New, Open, Save, Save As
            CommandGroup(replacing: .newItem) {
                Button("New Project") {
                    appState.requestNewProject()
                }
                .keyboardShortcut("n", modifiers: .command)

                Button("Open...") {
                    Task { await appState.openProjectFile() }
                }
                .keyboardShortcut("o", modifiers: .command)

                Menu("Open Recent") {
                    if RecentFiles.shared.paths.isEmpty {
                        Text("No Recent Files")
                    } else {
                        ForEach(RecentFiles.shared.paths, id: \.self) { url in
                            Button(url.lastPathComponent) {
                                Task { await appState.loadProjectFromURL(url) }
                            }
                        }

                        Divider()

                        Button("Clear List") {
                            RecentFiles.shared.clear()
                        }
                    }
                }

                Divider()

                Button("Save") {
                    Task { await appState.saveProjectFile() }
                }
                .keyboardShortcut("s", modifiers: .command)

                Button("Save As...") {
                    Task { await appState.saveProjectFileAs() }
                }
                .keyboardShortcut("s", modifiers: [.command, .shift])
            }

            // Replace the default About menu item
            CommandGroup(replacing: .appInfo) {
                Button("About Refraction") {
                    NSApplication.shared.orderFrontStandardAboutPanel(
                        options: [
                            .applicationName: "Refraction",
                            .applicationVersion: appVersion,
                            .version: buildVersion,
                            .credits: aboutCredits,
                        ]
                    )
                }
            }
        }
    }

    // MARK: - About Dialog

    private var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.1.0"
    }

    private var buildVersion: String {
        Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1"
    }

    private var aboutCredits: NSAttributedString {
        let text = """
        Scientific plotting and analysis for macOS.

        Built by Ashwin Pasupathy and Claude (Anthropic).
        """
        return NSAttributedString(
            string: text,
            attributes: [
                .font: NSFont.systemFont(ofSize: 11),
                .foregroundColor: NSColor.secondaryLabelColor,
            ]
        )
    }
}
