## WebSocket client for the Trading Platform backend.
## Connects to FastAPI, receives candle data + indicators + ML signals.
extends Node
class_name MarketClient

signal connected
signal disconnected
signal candles_received(data: Dictionary)
signal candle_updated(data: Dictionary)
signal ml_signal_received(data: Dictionary)
signal connection_error(message: String)

@export var server_host: String = "milo.local"
@export var server_port: int = 8770

var _socket: WebSocketPeer = WebSocketPeer.new()
var _is_connected: bool = false
var _current_symbol: String = ""

func _ready() -> void:
	set_process(false)

func connect_to_symbol(symbol: String, period: String = "6mo", interval: String = "1d") -> void:
	"""Connect to the WebSocket stream for a given symbol."""
	_current_symbol = symbol
	var url = "ws://%s:%d/ws/market/%s?period=%s&interval=%s" % [
		server_host, server_port, symbol, period, interval
	]
	print("[MarketClient] Connecting to: ", url)
	var err = _socket.connect_to_url(url)
	if err != OK:
		connection_error.emit("Failed to initiate connection: %d" % err)
		return
	set_process(true)

func disconnect_from_server() -> void:
	_socket.close()
	_is_connected = false
	set_process(false)
	disconnected.emit()

func _process(_delta: float) -> void:
	_socket.poll()
	var state = _socket.get_ready_state()

	match state:
		WebSocketPeer.STATE_OPEN:
			if not _is_connected:
				_is_connected = true
				print("[MarketClient] Connected!")
				connected.emit()
			while _socket.get_available_packet_count() > 0:
				var packet = _socket.get_packet()
				_handle_message(packet.get_string_from_utf8())

		WebSocketPeer.STATE_CLOSING:
			pass

		WebSocketPeer.STATE_CLOSED:
			if _is_connected:
				_is_connected = false
				var code = _socket.get_close_code()
				print("[MarketClient] Disconnected: code=%d" % code)
				disconnected.emit()
			set_process(false)

func _handle_message(raw: String) -> void:
	var json = JSON.new()
	var err = json.parse(raw)
	if err != OK:
		print("[MarketClient] JSON parse error: ", json.get_error_message())
		return

	var data: Dictionary = json.data

	match data.get("type", ""):
		"init":
			print("[MarketClient] Received init: %d candles" % data.candles.size())
			candles_received.emit(data)
			if data.has("ml_signal"):
				ml_signal_received.emit(data.ml_signal)

		"update":
			candle_updated.emit(data)
			if data.has("ml_signal"):
				ml_signal_received.emit(data.ml_signal)

		_:
			print("[MarketClient] Unknown message type: ", data.get("type"))
