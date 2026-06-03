// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "IVRBeacon",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "IVRBeacon",
            path: "Sources/IVRBeacon"
        )
    ]
)
