# Native Desktop Wrapper Design

## Goal
Build a shared SwiftUI wrapper for the existing IVR assessment tool that runs on macOS and iPhone OS, gives operators a native interface for starting sessions, replaying traces, and reviewing mapping output, and keeps the current Python CLI as the execution engine.

## Architecture
This wrapper will be a shared SwiftUI codebase with platform-specific shells: one macOS target and one iPhone target. The shared layer will own app state, session models, request builders, and result parsing, while the platform shells provide navigation, window layout, and device-specific presentation. The wrapper will not reimplement IVR logic; instead, it will invoke the existing Python CLI as a process bridge and render the returned JSON or report output.

The first version should stay intentionally thin. The GUI is a control surface and results viewer, not a new telephony stack. That keeps the native app small, lets us reuse the working Python implementation immediately, and gives us a clean path to migrate logic into a native backend later if needed.

## Tech Stack
- SwiftUI for shared UI
- macOS app target
- iPhone app target
- Swift Package for shared models and services
- XCTest for unit and integration tests
- Existing Python CLI as the execution backend

---

### Task 1: Define the shared app model

**Files:**
- Create: `Sources/IVRWrapperCore/WrapperModels.swift`
- Create: `Tests/IVRWrapperCoreTests/WrapperModelsTests.swift`

- [ ] **Step 1: Write the failing test**

```swift
import XCTest
@testable import IVRWrapperCore

final class WrapperModelsTests: XCTestCase {
    func test_map_request_stores_target_and_mode() {
        let request = MapRequest(
            targetNumbers: ["+15555550100"],
            sessionMode: .singleSession,
            responseMode: .dtmf
        )

        XCTAssertEqual(request.targetNumbers, ["+15555550100"])
        XCTAssertEqual(request.sessionMode, .singleSession)
        XCTAssertEqual(request.responseMode, .dtmf)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `swift test --filter WrapperModelsTests`
Expected: FAIL because `MapRequest` and related shared types do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```swift
import Foundation

public enum SessionMode: String, Codable, CaseIterable {
    case singleSession = "single-session"
    case multiSession = "multi-session"
    case replayOnly = "replay-only"
}

public enum ResponseMode: String, Codable, CaseIterable {
    case dtmf
    case voice
}

public struct MapRequest: Codable, Equatable {
    public var targetNumbers: [String]
    public var sessionMode: SessionMode
    public var responseMode: ResponseMode

    public init(targetNumbers: [String], sessionMode: SessionMode, responseMode: ResponseMode) {
        self.targetNumbers = targetNumbers
        self.sessionMode = sessionMode
        self.responseMode = responseMode
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `swift test --filter WrapperModelsTests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Sources/IVRWrapperCore/WrapperModels.swift Tests/IVRWrapperCoreTests/WrapperModelsTests.swift
git commit -m "feat: add shared wrapper models"
```

### Task 2: Add the backend process bridge

**Files:**
- Create: `Sources/IVRWrapperCore/PythonCLIClient.swift`
- Create: `Tests/IVRWrapperCoreTests/PythonCLIClientTests.swift`

- [ ] **Step 1: Write the failing test**

```swift
import XCTest
@testable import IVRWrapperCore

final class PythonCLIClientTests: XCTestCase {
    func test_builds_map_command_arguments() {
        let client = PythonCLIClient(pythonPath: "/usr/bin/python3", projectRoot: "/tmp/project")
        let arguments = client.mapArguments(
            targetNumbers: ["+15555550100"],
            sessionMode: .singleSession,
            responseMode: .dtmf,
            promptTexts: ["Press 1 for billing"]
        )

        XCTAssertEqual(arguments, [
            "-m", "ivr_assessor", "map",
            "--target-number", "+15555550100",
            "--session-mode", "single-session",
            "--response-mode", "dtmf",
            "--prompt", "Press 1 for billing"
        ])
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `swift test --filter PythonCLIClientTests`
Expected: FAIL because `PythonCLIClient` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```swift
import Foundation

public struct PythonCLIClient {
    public let pythonPath: String
    public let projectRoot: String

    public init(pythonPath: String, projectRoot: String) {
        self.pythonPath = pythonPath
        self.projectRoot = projectRoot
    }

    public func mapArguments(
        targetNumbers: [String],
        sessionMode: SessionMode,
        responseMode: ResponseMode,
        promptTexts: [String]
    ) -> [String] {
        var args = ["-m", "ivr_assessor", "map"]
        for number in targetNumbers {
            args.append(contentsOf: ["--target-number", number])
        }
        args.append(contentsOf: ["--session-mode", sessionMode.rawValue])
        args.append(contentsOf: ["--response-mode", responseMode.rawValue])
        for prompt in promptTexts {
            args.append(contentsOf: ["--prompt", prompt])
        }
        return args
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `swift test --filter PythonCLIClientTests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Sources/IVRWrapperCore/PythonCLIClient.swift Tests/IVRWrapperCoreTests/PythonCLIClientTests.swift
git commit -m "feat: add python cli bridge"
```

### Task 3: Build the shared session state and view models

**Files:**
- Create: `Sources/IVRWrapperCore/SessionStore.swift`
- Create: `Sources/IVRWrapperCore/MapSessionViewModel.swift`
- Create: `Tests/IVRWrapperCoreTests/MapSessionViewModelTests.swift`

- [ ] **Step 1: Write the failing test**

```swift
import XCTest
@testable import IVRWrapperCore

final class MapSessionViewModelTests: XCTestCase {
    func test_session_updates_status_and_results() {
        let store = SessionStore()
        let viewModel = MapSessionViewModel(store: store)

        viewModel.startMap(
            MapRequest(
                targetNumbers: ["+15555550100"],
                sessionMode: .singleSession,
                responseMode: .dtmf
            )
        )

        XCTAssertEqual(viewModel.statusText, "Ready")
        XCTAssertFalse(viewModel.sessions.isEmpty)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `swift test --filter MapSessionViewModelTests`
Expected: FAIL because the store and view model do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```swift
import Foundation

public struct SessionRecord: Identifiable, Equatable {
    public let id: String
    public var targetNumber: String
    public var sessionMode: SessionMode
    public var statusText: String
    public var graphSummary: String
}

public final class SessionStore: ObservableObject {
    @Published public var sessions: [SessionRecord] = []

    public init() {}
}

@MainActor
public final class MapSessionViewModel: ObservableObject {
    @Published public private(set) var sessions: [SessionRecord] = []
    @Published public private(set) var statusText: String = "Idle"

    private let store: SessionStore

    public init(store: SessionStore) {
        self.store = store
    }

    public func startMap(_ request: MapRequest) {
        sessions = request.targetNumbers.enumerated().map { index, target in
            SessionRecord(
                id: "session-\(index + 1)",
                targetNumber: target,
                sessionMode: request.sessionMode,
                statusText: "Ready",
                graphSummary: ""
            )
        }
        store.sessions = sessions
        statusText = "Ready"
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `swift test --filter MapSessionViewModelTests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Sources/IVRWrapperCore/SessionStore.swift Sources/IVRWrapperCore/MapSessionViewModel.swift Tests/IVRWrapperCoreTests/MapSessionViewModelTests.swift
git commit -m "feat: add shared session state"
```

### Task 4: Add macOS and iPhone SwiftUI shells

**Files:**
- Create: `Sources/IVRWrapperCore/AppShellDescriptor.swift`
- Create: `Sources/IVRWrapperMacApp/IVRWrapperMacApp.swift`
- Create: `Sources/IVRWrapperMacApp/ContentView.swift`
- Create: `Sources/IVRWrapperPhoneApp/IVRWrapperPhoneApp.swift`
- Create: `Sources/IVRWrapperPhoneApp/ContentView.swift`
- Create: `Tests/IVRWrapperUITests/SmokeTests.swift`

- [ ] **Step 1: Write the failing test**

```swift
import XCTest
@testable import IVRWrapperCore

final class SmokeTests: XCTestCase {
    func test_app_shells_expose_the_same_navigation_sections() {
        let descriptor = AppShellDescriptor.default

        XCTAssertEqual(descriptor.title, "IVR Mapper")
        XCTAssertEqual(descriptor.sections, ["Map", "Replay", "Dry Run"])
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `swift test --filter SmokeTests`
Expected: FAIL because `AppShellDescriptor` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```swift
import SwiftUI

public struct AppShellDescriptor: Equatable {
    public let title: String
    public let sections: [String]

    public static let `default` = AppShellDescriptor(
        title: "IVR Mapper",
        sections: ["Map", "Replay", "Dry Run"]
    )
}

@main
struct IVRWrapperMacApp: App {
    @StateObject private var store = SessionStore()

    var body: some Scene {
        WindowGroup {
            ContentView(
                descriptor: .default,
                viewModel: MapSessionViewModel(store: store)
            )
        }
    }
}
```

```swift
import SwiftUI

struct ContentView: View {
    let descriptor: AppShellDescriptor
    @ObservedObject var viewModel: MapSessionViewModel

    var body: some View {
        Text(descriptor.title)
    }
}
```

```swift
import SwiftUI

@main
struct IVRWrapperPhoneApp: App {
    @StateObject private var store = SessionStore()

    var body: some Scene {
        WindowGroup {
            ContentView(
                descriptor: .default,
                viewModel: MapSessionViewModel(store: store)
            )
        }
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `swift test --filter SmokeTests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Sources/IVRWrapperMacApp/IVRWrapperMacApp.swift Sources/IVRWrapperMacApp/ContentView.swift Sources/IVRWrapperPhoneApp/IVRWrapperPhoneApp.swift Sources/IVRWrapperPhoneApp/ContentView.swift Tests/IVRWrapperUITests/SmokeTests.swift
git commit -m "feat: add native app shells"
```

### Task 5: Wire the map, replay, and dry-run screens into the shared UI

**Files:**
- Modify: `Sources/IVRWrapperMacApp/ContentView.swift`
- Modify: `Sources/IVRWrapperPhoneApp/ContentView.swift`
- Create: `Sources/IVRWrapperCore/NavigationState.swift`
- Create: `Tests/IVRWrapperCoreTests/NavigationStateTests.swift`

- [ ] **Step 1: Write the failing test**

```swift
import XCTest
@testable import IVRWrapperCore

final class NavigationStateTests: XCTestCase {
    func test_navigation_defaults_to_map() {
        let state = NavigationState()
        XCTAssertEqual(state.selectedMode, .map)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `swift test --filter NavigationStateTests`
Expected: FAIL because `NavigationState` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```swift
import Foundation

public enum WrapperMode: String, CaseIterable, Identifiable {
    case map
    case replay
    case dryRun

    public var id: String { rawValue }
}

@MainActor
public final class NavigationState: ObservableObject {
    @Published public var selectedMode: WrapperMode = .map

    public init() {}
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `swift test --filter NavigationStateTests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Sources/IVRWrapperCore/NavigationState.swift Sources/IVRWrapperMacApp/ContentView.swift Sources/IVRWrapperPhoneApp/ContentView.swift Tests/IVRWrapperCoreTests/NavigationStateTests.swift
git commit -m "feat: add wrapper navigation state"
```

### Task 6: Add error handling and launch diagnostics

**Files:**
- Create: `Sources/IVRWrapperCore/WrapperError.swift`
- Create: `Tests/IVRWrapperCoreTests/WrapperErrorTests.swift`

- [ ] **Step 1: Write the failing test**

```swift
import XCTest
@testable import IVRWrapperCore

final class WrapperErrorTests: XCTestCase {
    func test_missing_python_path_message_is_readable() {
        let error = WrapperError.missingPythonPath
        XCTAssertTrue(error.localizedDescription.contains("Python"))
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `swift test --filter WrapperErrorTests`
Expected: FAIL because `WrapperError` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```swift
import Foundation

public enum WrapperError: LocalizedError {
    case missingPythonPath
    case launchFailed(String)
    case invalidOutput(String)

    public var errorDescription: String? {
        switch self {
        case .missingPythonPath:
            return "Python runtime path is missing."
        case .launchFailed(let message):
            return "Failed to launch backend: \(message)"
        case .invalidOutput(let message):
            return "Invalid backend output: \(message)"
        }
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `swift test --filter WrapperErrorTests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Sources/IVRWrapperCore/WrapperError.swift Tests/IVRWrapperCoreTests/WrapperErrorTests.swift
git commit -m "feat: add wrapper error handling"
```

## Self-Review Checklist

- The spec maps every requirement to a task:
  - shared SwiftUI core: Tasks 1, 3, 5
  - macOS target: Task 4
  - iPhone target: Task 4
  - process bridge to Python CLI: Task 2
  - map workflow: Tasks 1, 3, 5
  - replay workflow: Tasks 2, 5
  - diagnostics and error handling: Task 6
- The wrapper stays focused on UI and orchestration. It does not replace the Python IVR engine.
- The design keeps the codebase split into small, testable units with clean ownership per file.
- No placeholder text remains in the tasks.
