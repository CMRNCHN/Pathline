import React, { useState, useEffect, useRef, useCallback } from 'react';

const PathlineDashboard = () => {
  const [activeCalls, setActiveCalls] = useState([]);
  const [selectedCall, setSelectedCall] = useState(null);
  const [sessionState, setSessionState] = useState(null);
  const [flowMap, setFlowMap] = useState(null);
  const [transcriptSegments, setTranscriptSegments] = useState([]);
  const [dtmfInput, setDtmfInput] = useState('');
  const [voiceInput, setVoiceInput] = useState('');
  const [suites, setSuites] = useState({});
  const [mapLayout, setMapLayout] = useState('cytoscape');
  const wsRef = useRef(null);
  const cytoscapeRef = useRef(null);

  // Fetch active sessions
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/sessions/active');
        const data = await res.json();
        setActiveCalls(data.sessions || []);
      } catch (err) {
        console.error('Failed to fetch sessions:', err);
      }
    };

    fetchSessions();
    const interval = setInterval(fetchSessions, 2000);
    return () => clearInterval(interval);
  }, []);

  // Fetch available suites
  useEffect(() => {
    const fetchSuites = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/suites');
        const data = await res.json();
        setSuites(data.suites || {});
      } catch (err) {
        console.error('Failed to fetch suites:', err);
      }
    };

    fetchSuites();
  }, []);

  // Connect to WebSocket for selected call
  useEffect(() => {
    if (!selectedCall) return;

    const connectWebSocket = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/session/${selectedCall}`);
        const data = await res.json();
        setSessionState(data);
        setTranscriptSegments(data.transcript_segments || []);
      } catch (err) {
        console.error('Failed to fetch session:', err);
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//localhost:8000/live/${selectedCall}`;

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.event === 'transcript') {
          setTranscriptSegments((prev) => [...prev, message.data]);
        } else if (message.event === 'flow_map') {
          setFlowMap(message.data);
          renderCytoscape(message.data);
        } else if (message.event === 'map_update') {
          setFlowMap(message.data);
          renderCytoscape(message.data);
        }
      };

      wsRef.current.onerror = (err) => {
        console.error('WebSocket error:', err);
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket closed');
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [selectedCall]);

  // Fetch flow map when call is selected
  useEffect(() => {
    if (!selectedCall) return;

    const fetchMap = async () => {
      try {
        const res = await fetch(
          `http://localhost:8000/api/map/${selectedCall}?format=cytoscape`
        );
        const data = await res.json();
        setFlowMap(data);
        renderCytoscape(data);
      } catch (err) {
        console.error('Failed to fetch map:', err);
      }
    };

    fetchMap();
  }, [selectedCall]);

  const renderCytoscape = useCallback((data) => {
    if (!cytoscapeRef.current || !data || !data.elements) return;

    const container = cytoscapeRef.current;
    container.innerHTML = '';

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('style', 'background: #f8f9fa; border: 1px solid #ddd;');

    const nodes = data.elements.filter((e) => e.data && !e.data.source);

    nodes.forEach((node, idx) => {
      const x = 50 + (idx % 5) * 180;
      const y = 50 + Math.floor(idx / 5) * 150;

      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.setAttribute('transform', `translate(${x}, ${y})`);

      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('width', '160');
      rect.setAttribute('height', '80');
      rect.setAttribute('fill', '#007bff');
      rect.setAttribute('stroke', '#0056b3');
      rect.setAttribute('stroke-width', '2');
      rect.setAttribute('rx', '4');

      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', '80');
      text.setAttribute('y', '40');
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('fill', 'white');
      text.setAttribute('font-size', '12');
      text.setAttribute('font-weight', 'bold');
      text.textContent = node.data.label.substring(0, 20);

      g.appendChild(rect);
      g.appendChild(text);
      svg.appendChild(g);
    });

    container.appendChild(svg);
  }, []);

  const sendDTMF = async () => {
    if (!selectedCall || !dtmfInput) return;

    try {
      await fetch('http://localhost:8000/api/dtmf/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ call_sid: selectedCall, dtmf: dtmfInput }),
      });
      setDtmfInput('');
    } catch (err) {
      console.error('Failed to send DTMF:', err);
    }
  };

  const injectVoice = async () => {
    if (!selectedCall || !voiceInput) return;

    try {
      await fetch('http://localhost:8000/api/voice/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ call_sid: selectedCall, text: voiceInput }),
      });
      setVoiceInput('');
    } catch (err) {
      console.error('Failed to inject voice:', err);
    }
  };

  const executeSuite = async (suiteName) => {
    if (!selectedCall) return;

    try {
      await fetch('http://localhost:8000/api/suites/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ call_sid: selectedCall, suite_name: suiteName }),
      });
    } catch (err) {
      console.error('Failed to execute suite:', err);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'sans-serif' }}>
      {/* Sidebar: Active Calls */}
      <div style={{ width: '250px', borderRight: '1px solid #ddd', overflowY: 'auto' }}>
        <div style={{ padding: '16px', fontWeight: 'bold', fontSize: '14px' }}>
          Active Calls ({activeCalls.length})
        </div>
        {activeCalls.map((call) => (
          <div
            key={call.call_sid}
            onClick={() => setSelectedCall(call.call_sid)}
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid #eee',
              cursor: 'pointer',
              background: selectedCall === call.call_sid ? '#e7f3ff' : 'transparent',
              borderLeft:
                selectedCall === call.call_sid
                  ? '4px solid #007bff'
                  : '4px solid transparent',
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 'bold' }}>
              {call.call_sid.substring(0, 12)}
            </div>
            <div style={{ fontSize: '11px', color: '#666' }}>
              {call.phone_number || 'Unknown'}
            </div>
            {call.suite_name && (
              <div style={{ fontSize: '10px', color: '#0056b3' }}>
                Suite: {call.suite_name}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {selectedCall ? (
          <>
            <div
              style={{
                borderBottom: '1px solid #ddd',
                padding: '16px',
                background: '#f8f9fa',
              }}
            >
              <div style={{ fontWeight: 'bold', fontSize: '16px' }}>
                Call: {selectedCall}
              </div>
              {sessionState && (
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  Segments: {sessionState.transcript_segments?.length || 0} | Nodes:{' '}
                  {flowMap?.elements?.filter((e) => !e.data?.source).length || 0}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
              {/* Transcript */}
              <div
                style={{
                  width: '30%',
                  borderRight: '1px solid #ddd',
                  overflowY: 'auto',
                }}
              >
                <div style={{ padding: '16px', fontWeight: 'bold' }}>Transcript</div>
                {transcriptSegments.map((seg, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '12px 16px',
                      borderBottom: '1px solid #eee',
                      fontSize: '12px',
                    }}
                  >
                    <div>{seg.text}</div>
                    <div style={{ color: '#999', fontSize: '10px', marginTop: '4px' }}>
                      Conf: {(seg.confidence * 100).toFixed(0)}% | {seg.start?.toFixed(1)}s
                    </div>
                  </div>
                ))}
              </div>

              {/* Map & Controls */}
              <div style={{ width: '70%', display: 'flex', flexDirection: 'column' }}>
                <div style={{ padding: '16px', fontWeight: 'bold' }}>Flow Map</div>
                <div ref={cytoscapeRef} style={{ flex: 1, borderBottom: '1px solid #ddd' }} />

                <div style={{ padding: '16px', borderTop: '1px solid #ddd' }}>
                  {/* DTMF */}
                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold' }}>
                      DTMF
                    </label>
                    <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                      <input
                        type="text"
                        value={dtmfInput}
                        onChange={(e) => setDtmfInput(e.target.value)}
                        placeholder="1,500,2"
                        style={{
                          flex: 1,
                          padding: '6px',
                          fontSize: '12px',
                          border: '1px solid #ddd',
                          borderRadius: '3px',
                        }}
                      />
                      <button
                        onClick={sendDTMF}
                        style={{
                          padding: '6px 12px',
                          background: '#007bff',
                          color: 'white',
                          border: 'none',
                          borderRadius: '3px',
                          cursor: 'pointer',
                          fontSize: '12px',
                        }}
                      >
                        Send
                      </button>
                    </div>
                  </div>

                  {/* Voice */}
                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold' }}>
                      Voice
                    </label>
                    <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                      <input
                        type="text"
                        value={voiceInput}
                        onChange={(e) => setVoiceInput(e.target.value)}
                        placeholder="What menu options do you have?"
                        style={{
                          flex: 1,
                          padding: '6px',
                          fontSize: '12px',
                          border: '1px solid #ddd',
                          borderRadius: '3px',
                        }}
                      />
                      <button
                        onClick={injectVoice}
                        style={{
                          padding: '6px 12px',
                          background: '#28a745',
                          color: 'white',
                          border: 'none',
                          borderRadius: '3px',
                          cursor: 'pointer',
                          fontSize: '12px',
                        }}
                      >
                        Inject
                      </button>
                    </div>
                  </div>

                  {/* Suites */}
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold' }}>
                      Test Suites
                    </label>
                    <div
                      style={{
                        display: 'flex',
                        gap: '4px',
                        flexWrap: 'wrap',
                        marginTop: '4px',
                      }}
                    >
                      {Object.entries(suites).map(([name, suite]) => (
                        <button
                          key={name}
                          onClick={() => executeSuite(name)}
                          style={{
                            padding: '4px 8px',
                            background: '#6c757d',
                            color: 'white',
                            border: 'none',
                            borderRadius: '3px',
                            cursor: 'pointer',
                            fontSize: '11px',
                          }}
                        >
                          {suite.name}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flex: 1,
              color: '#999',
            }}
          >
            Select a call to view details
          </div>
        )}
      </div>
    </div>
  );
};

export default PathlineDashboard;
