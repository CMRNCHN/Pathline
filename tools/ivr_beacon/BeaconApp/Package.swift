// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "PathlinePulse",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "PathlinePulse",
            path: "Sources/PathlinePulse"
        ),
        .testTarget(
            name: "PathlinePulseTests",
            dependencies: ["PathlinePulse"],
            path: "Tests/PathlinePulseTests"
        )
    ]
)
