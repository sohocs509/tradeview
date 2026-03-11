## Main scene controller.
## Manages the UI layout, symbol selection, and data flow.
extends Control

@onready var market_client: MarketClient = $MarketClient
@onready var chart: CandlestickChart = $MainLayout/ChartArea/CandlestickChart
@onready var rsi_panel: IndicatorPanel = $MainLayout/RSIPanel
@onready var macd_panel: IndicatorPanel = $MainLayout/MACDPanel
@onready var symbol_input: LineEdit = $MainLayout/TopBar/SymbolInput
@onready var connect_btn: Button = $MainLayout/TopBar/ConnectBtn
@onready var status_label: Label = $MainLayout/TopBar/StatusLabel
@onready var signal_label: Label = $MainLayout/TopBar/SignalLabel
@onready var sma_toggle: CheckButton = $MainLayout/TopBar/SMAToggle
@onready var bb_toggle: CheckButton = $MainLayout/TopBar/BBToggle

var current_symbol: String = "SPY"

func _ready() -> void:
	# Wire signals
	market_client.connected.connect(_on_connected)
	market_client.disconnected.connect(_on_disconnected)
	market_client.candles_received.connect(_on_candles_received)
	market_client.candle_updated.connect(_on_candle_updated)
	market_client.ml_signal_received.connect(_on_ml_signal)
	market_client.connection_error.connect(_on_connection_error)

	connect_btn.pressed.connect(_on_connect_pressed)
	sma_toggle.toggled.connect(_on_sma_toggled)
	bb_toggle.toggled.connect(_on_bb_toggled)

	# Defaults
	symbol_input.text = current_symbol
	sma_toggle.button_pressed = true
	bb_toggle.button_pressed = true
	rsi_panel.mode = IndicatorPanel.Mode.RSI
	macd_panel.mode = IndicatorPanel.Mode.MACD
	status_label.text = "Disconnected"

func _on_connect_pressed() -> void:
	var sym = symbol_input.text.strip_edges().to_upper()
	if sym.is_empty():
		return
	current_symbol = sym
	market_client.disconnect_from_server()
	status_label.text = "Connecting..."
	chart.symbol = sym
	market_client.connect_to_symbol(sym)

func _on_connected() -> void:
	status_label.text = "Connected: " + current_symbol
	status_label.add_theme_color_override("font_color", Color(0.18, 0.8, 0.44))

func _on_disconnected() -> void:
	status_label.text = "Disconnected"
	status_label.add_theme_color_override("font_color", Color(0.91, 0.3, 0.24))

func _on_connection_error(msg: String) -> void:
	status_label.text = "Error: " + msg
	status_label.add_theme_color_override("font_color", Color(1.0, 0.5, 0.2))

func _on_candles_received(data: Dictionary) -> void:
	var candles = data.get("candles", [])
	chart.set_candles(candles)
	_sync_sub_panels()

func _on_candle_updated(data: Dictionary) -> void:
	var candle = data.get("candle", {})
	if not candle.is_empty():
		chart.update_candle(candle)
		_sync_sub_panels()

func _on_ml_signal(sig: Dictionary) -> void:
	chart.set_ml_signal(sig)
	var signal_text = sig.get("signal", "neutral").to_upper()
	var confidence = sig.get("confidence", 0.0)
	signal_label.text = "ML: %s (%.0f%%)" % [signal_text, confidence * 100]
	match sig.get("signal", ""):
		"bullish":
			signal_label.add_theme_color_override("font_color", Color(0.18, 0.8, 0.44))
		"bearish":
			signal_label.add_theme_color_override("font_color", Color(0.91, 0.3, 0.24))
		_:
			signal_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))

func _on_sma_toggled(pressed: bool) -> void:
	chart.show_sma20 = pressed
	chart.show_sma50 = pressed
	chart.queue_redraw()

func _on_bb_toggled(pressed: bool) -> void:
	chart.show_bbands = pressed
	chart.queue_redraw()

func _sync_sub_panels() -> void:
	rsi_panel.set_data(chart.candles, chart.visible_start, chart.visible_count)
	macd_panel.set_data(chart.candles, chart.visible_start, chart.visible_count)

func _input(event: InputEvent) -> void:
	# Sync sub-panels when chart scrolls/zooms
	if event is InputEventMouseButton or event is InputEventMouseMotion:
		_sync_sub_panels()
