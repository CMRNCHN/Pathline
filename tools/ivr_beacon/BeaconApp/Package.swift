// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "PathlinePulse",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "PathlinePulse",
            path: "Sources/PathlinePulse"
        )
    ]
)
