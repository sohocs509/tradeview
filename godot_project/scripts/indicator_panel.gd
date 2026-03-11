## RSI and MACD indicator sub-panel.
## Rendered below the candlestick chart.
extends Control
class_name IndicatorPanel

@export var rsi_color: Color = Color(0.6, 0.4, 1.0)
@export var macd_color: Color = Color(0.2, 0.8, 0.6)
@export var macd_signal_color: Color = Color(1.0, 0.5, 0.2)
@export var macd_hist_bull: Color = Color(0.18, 0.8, 0.44, 0.5)
@export var macd_hist_bear: Color = Color(0.91, 0.3, 0.24, 0.5)
@export var bg_color: Color = Color(0.06, 0.07, 0.09)
@export var grid_color: Color = Color(1, 1, 1, 0.05)
@export var text_color: Color = Color(0.6, 0.6, 0.6)
@export var overbought_color: Color = Color(0.91, 0.3, 0.24, 0.15)
@export var oversold_color: Color = Color(0.18, 0.8, 0.44, 0.15)

enum Mode { RSI, MACD }
@export var mode: Mode = Mode.RSI

var candles: Array = []
var visible_start: int = 0
var visible_count: int = 80

func set_data(data: Array, start: int, count: int) -> void:
	candles = data
	visible_start = start
	visible_count = count
	queue_redraw()

func _draw() -> void:
	var rect = get_rect()
	draw_rect(Rect2(Vector2.ZERO, rect.size), bg_color)

	if candles.is_empty():
		return

	var margin_x = 80.0
	var margin_y = 4.0
	var area = Rect2(margin_x, margin_y, rect.size.x - margin_x * 2, rect.size.y - margin_y * 2)
	var end_idx = min(visible_start + visible_count, candles.size())
	var count = end_idx - visible_start
	if count <= 0:
		return

	var candle_spacing = 2.0
	var candle_w = (area.size.x - candle_spacing * count) / count

	match mode:
		Mode.RSI:
			_draw_rsi(area, candle_w, candle_spacing, count)
		Mode.MACD:
			_draw_macd(area, candle_w, candle_spacing, count)

func _draw_rsi(area: Rect2, cw: float, spacing: float, count: int) -> void:
	var font = ThemeDB.fallback_font

	# Overbought/oversold zones
	var y70 = area.position.y + (1.0 - 70.0 / 100.0) * area.size.y
	var y30 = area.position.y + (1.0 - 30.0 / 100.0) * area.size.y
	draw_rect(Rect2(area.position.x, area.position.y, area.size.x, y70 - area.position.y), overbought_color)
	draw_rect(Rect2(area.position.x, y30, area.size.x, area.end.y - y30), oversold_color)

	# Reference lines
	for level in [30.0, 50.0, 70.0]:
		var y = area.position.y + (1.0 - level / 100.0) * area.size.y
		draw_line(Vector2(area.position.x, y), Vector2(area.end.x, y), grid_color, 1.0)
		draw_string(font, Vector2(4, y + 4), str(int(level)), HORIZONTAL_ALIGNMENT_LEFT, -1, 10, text_color)

	# RSI line
	var points: PackedVector2Array = []
	for i in range(count):
		var idx = visible_start + i
		var c = candles[idx]
		if c.has("RSI_14"):
			var x = area.position.x + i * (cw + spacing) + cw / 2.0
			var y = area.position.y + (1.0 - c["RSI_14"] / 100.0) * area.size.y
			points.append(Vector2(x, y))
	if points.size() > 1:
		draw_polyline(points, rsi_color, 1.5, true)

	# Label
	draw_string(font, Vector2(area.position.x + 4, area.position.y + 12), "RSI(14)", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, rsi_color)

func _draw_macd(area: Rect2, cw: float, spacing: float, count: int) -> void:
	var font = ThemeDB.fallback_font

	# Find MACD range
	var macd_min: float = INF
	var macd_max: float = -INF
	for i in range(count):
		var idx = visible_start + i
		var c = candles[idx]
		for key in ["MACD_12_26_9", "MACDs_12_26_9", "MACDh_12_26_9"]:
			if c.has(key):
				macd_min = min(macd_min, c[key])
				macd_max = max(macd_max, c[key])

	if macd_min == INF:
		return

	var padding = (macd_max - macd_min) * 0.1
	macd_min -= padding
	macd_max += padding

	# Zero line
	var zero_y = area.position.y + (macd_max / (macd_max - macd_min)) * area.size.y
	draw_line(Vector2(area.position.x, zero_y), Vector2(area.end.x, zero_y), grid_color, 1.0)

	# Histogram
	for i in range(count):
		var idx = visible_start + i
		var c = candles[idx]
		if c.has("MACDh_12_26_9"):
			var x = area.position.x + i * (cw + spacing)
			var val = c["MACDh_12_26_9"]
			var y = area.position.y + ((macd_max - val) / (macd_max - macd_min)) * area.size.y
			var bar_color = macd_hist_bull if val >= 0 else macd_hist_bear
			draw_rect(Rect2(x, min(y, zero_y), cw, abs(y - zero_y)), bar_color)

	# MACD and Signal lines
	var macd_points: PackedVector2Array = []
	var signal_points: PackedVector2Array = []
	for i in range(count):
		var idx = visible_start + i
		var c = candles[idx]
		var x = area.position.x + i * (cw + spacing) + cw / 2.0
		if c.has("MACD_12_26_9"):
			var y = area.position.y + ((macd_max - c["MACD_12_26_9"]) / (macd_max - macd_min)) * area.size.y
			macd_points.append(Vector2(x, y))
		if c.has("MACDs_12_26_9"):
			var y = area.position.y + ((macd_max - c["MACDs_12_26_9"]) / (macd_max - macd_min)) * area.size.y
			signal_points.append(Vector2(x, y))

	if macd_points.size() > 1:
		draw_polyline(macd_points, macd_color, 1.5, true)
	if signal_points.size() > 1:
		draw_polyline(signal_points, macd_signal_color, 1.5, true)

	draw_string(font, Vector2(area.position.x + 4, area.position.y + 12), "MACD(12,26,9)", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, macd_color)
