import Foundation

final class Uploader {
    func send(data: Data) {
        var request = URLRequest(url: URL(string: "http://localhost:7777/ingest")!)
        request.httpMethod = "POST"
        request.httpBody = data
        URLSession.shared.dataTask(with: request).resume()
    }
}
