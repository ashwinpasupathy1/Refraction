// RefractionApp.swift — Main entry point for the Refraction macOS app.
// Launches the Python analysis server on appear and stops it on disappear.

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
                }
                .onDisappear {
                    pythonServer.stop()
                }
        }
        .windowStyle(.titleBar)
        .defaultSize(width: 1200, height: 800)
    }
}
