## Candlestick chart renderer with indicator overlays.
## Draws OHLCV candles, SMA/EMA lines, Bollinger Bands, and volume bars.
extends Control
class_name CandlestickChart

# ── Appearance ──
@export var bull_color: Color = Color(0.18, 0.8, 0.44)     # Green
@export var bear_color: Color = Color(0.91, 0.3, 0.24)     # Red
@export var bg_color: Color = Color(0.08, 0.09, 0.11)      # Dark background
@export var grid_color: Color = Color(1, 1, 1, 0.06)
@export var text_color: Color = Color(0.7, 0.7, 0.7)
@export var sma20_color: Color = Color(1.0, 0.84, 0.0, 0.8)  # Gold
@export var sma50_color: Color = Color(0.4, 0.6, 1.0, 0.8)   # Blue
@export var bb_color: Color = Color(0.5, 0.5, 0.5, 0.3)      # Gray
@export var volume_bull: Color = Color(0.18, 0.8, 0.44, 0.3)
@export var volume_bear: Color = Color(0.91, 0.3, 0.24, 0.3)

# ── Layout ──
@export var chart_margin := Vector2(80, 40)  # left/right, top/bottom
@export var volume_height_ratio: float = 0.15
@export var candle_spacing: float = 2.0
@export var min_candle_width: float = 3.0
@export var max_candle_width: float = 20.0

# ── State ──
var candles: Array = []
var visible_start: int = 0
var visible_count: int = 80
var price_min: float = 0.0
var price_max: float = 0.0
var vol_max: float = 0.0
var symbol: String = ""
var ml_signal: Dictionary = {}

# ── Overlay toggles ──
var show_sma20: bool = true
var show_sma50: bool = true
var show_bbands: bool = true
var show_volume: bool = true

# ── Interaction ──
var _dragging: bool = false
var _drag_start_x: float = 0.0
var _drag_start_offset: int = 0
var _hover_index: int = -1

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP

func set_candles(data: Array) -> void:
	candles = data
	# Default view: show last N candles
	visible_start = max(0, candles.size() - visible_count)
	_recalc_range()
	queue_redraw()

func update_candle(candle: Dictionary) -> void:
	"""Append or update the latest candle."""
	if candles.size() > 0:
		var last = candles[candles.size() - 1]
		if last.get("timestamp", "") == candle.get("timestamp", ""):
			candles[candles.size() - 1] = candle
		else:
			candles.append(candle)
			visible_start = max(0, candles.size() - visible_count)
	else:
		candles.append(candle)
	_recalc_range()
	queue_redraw()

func set_ml_signal(sig: Dictionary) -> void:
	ml_signal = sig
	queue_redraw()

func _recalc_range() -> void:
	"""Recalculate visible price range and volume max."""
	if candles.is_empty():
		return
	var end_idx = min(visible_start + visible_count, candles.size())
	price_min = INF
	price_max = -INF
	vol_max = 0.0
	for i in range(visible_start, end_idx):
		var c = candles[i]
		price_min = min(price_min, c.get("low", 0.0))
		price_max = max(price_max, c.get("high", 0.0))
		vol_max = max(vol_max, c.get("volume", 0.0))
		# Extend range for Bollinger Bands
		if show_bbands:
			if c.has("BBL_20_2.0"):
				price_min = min(price_min, c["BBL_20_2.0"])
			if c.has("BBU_20_2.0"):
				price_max = max(price_max, c["BBU_20_2.0"])
	# Add padding
	var padding = (price_max - price_min) * 0.05
	price_min -= padding
	price_max += padding

func _draw() -> void:
	var rect = get_rect()
	# Background
	draw_rect(Rect2(Vector2.ZERO, rect.size), bg_color)

	if candles.is_empty():
		var font = ThemeDB.fallback_font
		draw_string(font, rect.size / 2 - Vector2(100, 0), "Connecting...", HORIZONTAL_ALIGNMENT_CENTER, -1, 16, text_color)
		return

	var chart_area = _get_chart_area(rect)
	var vol_area = _get_volume_area(rect)
	var end_idx = min(visible_start + visible_count, candles.size())
	var count = end_idx - visible_start
	if count <= 0:
		return

	var candle_w = clamp(
		(chart_area.size.x - candle_spacing * count) / count,
		min_candle_width,
		max_candle_width
	)

	_draw_grid(chart_area)
	_draw_price_axis(chart_area)

	# ── Bollinger Bands fill ──
	if show_bbands:
		_draw_bollinger_bands(chart_area, candle_w, count)

	# ── Candles + Volume ──
	for i in range(count):
		var idx = visible_start + i
		var c = candles[idx]
		var x = chart_area.position.x + i * (candle_w + candle_spacing)
		var is_bull = c.get("close", 0) >= c.get("open", 0)
		var color = bull_color if is_bull else bear_color

		# Candlestick body
		var y_open = _price_to_y(c.get("open", 0), chart_area)
		var y_close = _price_to_y(c.get("close", 0), chart_area)
		var y_high = _price_to_y(c.get("high", 0), chart_area)
		var y_low = _price_to_y(c.get("low", 0), chart_area)

		var body_top = min(y_open, y_close)
		var body_height = max(abs(y_close - y_open), 1.0)
		var wick_x = x + candle_w / 2.0

		# Wick
		draw_line(Vector2(wick_x, y_high), Vector2(wick_x, y_low), color, 1.0)
		# Body
		draw_rect(Rect2(x, body_top, candle_w, body_height), color)

		# Volume bar
		if show_volume and vol_max > 0:
			var vol_h = (c.get("volume", 0) / vol_max) * vol_area.size.y
			var vol_color = volume_bull if is_bull else volume_bear
			draw_rect(
				Rect2(x, vol_area.end.y - vol_h, candle_w, vol_h),
				vol_color
			)

	# ── Overlay lines ──
	if show_sma20:
		_draw_indicator_line("SMA_20", sma20_color, chart_area, candle_w, count)
	if show_sma50:
		_draw_indicator_line("SMA_50", sma50_color, chart_area, candle_w, count)

	# ── Crosshair / hover info ──
	if _hover_index >= 0 and _hover_index < candles.size():
		_draw_hover_info(rect)

	# ── ML Signal badge ──
	_draw_ml_badge(rect)

	# ── Symbol label ──
	var font = ThemeDB.fallback_font
	draw_string(font, Vector2(chart_margin.x + 8, 24), symbol, HORIZONTAL_ALIGNMENT_LEFT, -1, 18, text_color)


func _draw_grid(area: Rect2) -> void:
	var steps = 6
	for i in range(steps + 1):
		var y = area.position.y + (area.size.y / steps) * i
		draw_line(Vector2(area.position.x, y), Vector2(area.end.x, y), grid_color)

func _draw_price_axis(area: Rect2) -> void:
	var font = ThemeDB.fallback_font
	var steps = 6
	for i in range(steps + 1):
		var ratio = float(i) / steps
		var price = price_max - ratio * (price_max - price_min)
		var y = area.position.y + ratio * area.size.y
		var label = "%.2f" % price
		draw_string(font, Vector2(4, y + 4), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, text_color)

func _draw_indicator_line(key: String, color: Color, area: Rect2, candle_w: float, count: int) -> void:
	var points: PackedVector2Array = []
	for i in range(count):
		var idx = visible_start + i
		var c = candles[idx]
		if c.has(key):
			var x = area.position.x + i * (candle_w + candle_spacing) + candle_w / 2.0
			var y = _price_to_y(c[key], area)
			points.append(Vector2(x, y))
	if points.size() > 1:
		draw_polyline(points, color, 1.5, true)

func _draw_bollinger_bands(area: Rect2, candle_w: float, count: int) -> void:
	var upper_points: PackedVector2Array = []
	var lower_points: PackedVector2Array = []
	for i in range(count):
		var idx = visible_start + i
		var c = candles[idx]
		if c.has("BBU_20_2.0") and c.has("BBL_20_2.0"):
			var x = area.position.x + i * (candle_w + candle_spacing) + candle_w / 2.0
			upper_points.append(Vector2(x, _price_to_y(c["BBU_20_2.0"], area)))
			lower_points.append(Vector2(x, _price_to_y(c["BBL_20_2.0"], area)))

	if upper_points.size() > 1:
		draw_polyline(upper_points, bb_color, 1.0, true)
		draw_polyline(lower_points, bb_color, 1.0, true)
		# Fill between bands
		for i in range(upper_points.size() - 1):
			var poly = PackedVector2Array([
				upper_points[i], upper_points[i + 1],
				lower_points[i + 1], lower_points[i]
			])
			draw_colored_polygon(poly, Color(0.5, 0.5, 0.5, 0.05))

func _draw_ml_badge(rect: Rect2) -> void:
	if ml_signal.is_empty():
		return
	var font = ThemeDB.fallback_font
	var sig = ml_signal.get("signal", "neutral")
	var conf = ml_signal.get("confidence", 0.0)
	var badge_color: Color
	match sig:
		"bullish": badge_color = bull_color
		"bearish": badge_color = bear_color
		_: badge_color = Color(0.5, 0.5, 0.5)

	var badge_pos = Vector2(rect.size.x - 200, 10)
	draw_rect(Rect2(badge_pos, Vector2(185, 32)), badge_color * Color(1, 1, 1, 0.2))
	draw_rect(Rect2(badge_pos, Vector2(185, 32)), badge_color, false, 1.5)
	var label = "ML: %s (%.0f%%)" % [sig.to_upper(), conf * 100]
	draw_string(font, badge_pos + Vector2(10, 22), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, badge_color)

func _draw_hover_info(rect: Rect2) -> void:
	if _hover_index < 0 or _hover_index >= candles.size():
		return
	var c = candles[_hover_index]
	var font = ThemeDB.fallback_font
	var info = "O:%.2f H:%.2f L:%.2f C:%.2f V:%d" % [
		c.get("open", 0), c.get("high", 0), c.get("low", 0),
		c.get("close", 0), c.get("volume", 0)
	]
	draw_string(font, Vector2(chart_margin.x + 8, 44), info, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, text_color)

# ── Coordinate helpers ──

func _price_to_y(price: float, area: Rect2) -> float:
	if price_max == price_min:
		return area.position.y + area.size.y / 2.0
	var ratio = (price_max - price) / (price_max - price_min)
	return area.position.y + ratio * area.size.y

func _get_chart_area(rect: Rect2) -> Rect2:
	var vol_h = rect.size.y * volume_height_ratio
	return Rect2(
		chart_margin.x, chart_margin.y,
		rect.size.x - chart_margin.x * 2,
		rect.size.y - chart_margin.y * 2 - vol_h
	)

func _get_volume_area(rect: Rect2) -> Rect2:
	var vol_h = rect.size.y * volume_height_ratio
	return Rect2(
		chart_margin.x,
		rect.size.y - chart_margin.y - vol_h,
		rect.size.x - chart_margin.x * 2,
		vol_h
	)

# ── Input handling ──

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb = event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			_zoom(1)
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_zoom(-1)
		elif mb.button_index == MOUSE_BUTTON_LEFT:
			_dragging = mb.pressed
			if _dragging:
				_drag_start_x = mb.position.x
				_drag_start_offset = visible_start

	elif event is InputEventMouseMotion:
		var mm = event as InputEventMouseMotion
		_update_hover(mm.position)
		if _dragging:
			var dx = mm.position.x - _drag_start_x
			var chart_area = _get_chart_area(get_rect())
			var candle_w = chart_area.size.x / visible_count
			var offset = int(-dx / candle_w)
			visible_start = clamp(
				_drag_start_offset + offset,
				0,
				max(0, candles.size() - visible_count)
			)
			_recalc_range()
			queue_redraw()

func _zoom(direction: int) -> void:
	var old_count = visible_count
	visible_count = clamp(visible_count - direction * 5, 10, 300)
	if visible_count != old_count:
		visible_start = clamp(visible_start, 0, max(0, candles.size() - visible_count))
		_recalc_range()
		queue_redraw()

func _update_hover(pos: Vector2) -> void:
	var chart_area = _get_chart_area(get_rect())
	var count = min(visible_count, candles.size() - visible_start)
	if count <= 0:
		_hover_index = -1
		return
	var candle_w = (chart_area.size.x - candle_spacing * count) / count
	var rel_x = pos.x - chart_area.position.x
	var idx = int(rel_x / (candle_w + candle_spacing))
	if idx >= 0 and idx < count:
		_hover_index = visible_start + idx
	else:
		_hover_index = -1
	queue_redraw()
