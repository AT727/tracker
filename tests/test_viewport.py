import pytest

from tracker.canvas.viewport_state import ViewportState


def test_zoom_keeps_pixel_under_cursor_fixed():
    vp = ViewportState(scale=1.0, pan_x=0.0, pan_y=0.0)
    px, py = vp.scene_to_pixel(100.0, 200.0)
    vp.zoom_at(100.0, 200.0, 2.0)
    px2, py2 = vp.scene_to_pixel(100.0, 200.0)
    assert px2 == pytest.approx(px)
    assert py2 == pytest.approx(py)


def test_pixel_scene_round_trip():
    vp = ViewportState(scale=1.5, pan_x=10.0, pan_y=20.0)
    sx, sy = vp.pixel_to_scene(40.0, 50.0)
    px, py = vp.scene_to_pixel(sx, sy)
    assert px == pytest.approx(40.0)
    assert py == pytest.approx(50.0)


def test_zoom_with_letterbox_pan_keeps_scene_point_fixed():
    vp = ViewportState(scale=1.2, pan_x=80.0, pan_y=40.0)
    scene_x, scene_y = 200.0, 150.0
    px, py = vp.scene_to_pixel(scene_x, scene_y)
    vp.zoom_at(scene_x, scene_y, 1.5)
    px2, py2 = vp.scene_to_pixel(scene_x, scene_y)
    assert px2 == pytest.approx(px)
    assert py2 == pytest.approx(py)


def test_scene_to_pixel_is_identity_with_nonzero_pan():
    vp = ViewportState(scale=1.5, pan_x=50.0, pan_y=30.0)
    px, py = vp.scene_to_pixel(100.0, 200.0)
    assert px == pytest.approx(100.0)
    assert py == pytest.approx(200.0)


def test_view_to_pixel_with_letterbox():
    vp = ViewportState(scale=1.2, pan_x=80.0, pan_y=40.0)
    px, py = vp.view_to_pixel(320.0, 220.0)
    assert px == pytest.approx(200.0)
    assert py == pytest.approx(150.0)


def test_click_pixel_in_bounds_with_letterbox():
    """Regression: scene pixel (200, 150) must stay in bounds for 640x480 image."""
    vp = ViewportState(scale=1.2, pan_x=80.0, pan_y=40.0)
    image_w, image_h = 640, 480
    px, py = vp.scene_to_pixel(200.0, 150.0)
    assert 0 <= px <= image_w
    assert 0 <= py <= image_h


def test_pan_range_zero_when_image_fits():
    vp = ViewportState()
    vp.fit_to_view(800.0, 600.0, 640.0, 480.0)
    min_px, max_px, min_py, max_py = vp.pan_range(800.0, 600.0, 640.0, 480.0)
    assert min_px == pytest.approx(max_px)
    assert min_py == pytest.approx(max_py)


def test_pan_range_expands_when_zoomed_in():
    vp = ViewportState(scale=2.0, pan_x=0.0, pan_y=0.0)
    min_px, max_px, min_py, max_py = vp.pan_range(800.0, 600.0, 640.0, 480.0)
    assert max_px == pytest.approx(0.0)
    assert min_px < max_px
    assert max_py == pytest.approx(0.0)
    assert min_py < max_py


def test_set_pan_clamps_to_bounds():
    vp = ViewportState(scale=2.0, pan_x=0.0, pan_y=0.0)
    vp.set_pan(-999.0, 999.0, 800.0, 600.0, 640.0, 480.0)
    min_px, max_px, min_py, max_py = vp.pan_range(800.0, 600.0, 640.0, 480.0)
    assert vp.pan_x == pytest.approx(min_px)
    assert vp.pan_y == pytest.approx(max_py)


def test_pan_slider_round_trip():
    vp = ViewportState(scale=2.0, pan_x=-200.0, pan_y=-100.0)
    h_val, v_val, h_en, v_en = vp.pan_slider_values(800.0, 600.0, 640.0, 480.0)
    assert h_en
    assert v_en
    vp2 = ViewportState(scale=2.0)
    vp2.pan_from_sliders(h_val, v_val, 800.0, 600.0, 640.0, 480.0)
    assert vp2.pan_x == pytest.approx(vp.pan_x, abs=1.0)
    assert vp2.pan_y == pytest.approx(vp.pan_y, abs=1.0)


def test_vertical_pan_slider_direction_matches_modern_ux():
    """
    UX expectation:
    - dragging the vertical scrollbar "down" should move the viewport down
      (so `pan_y` should increase).
    """
    vp = ViewportState(scale=2.0, pan_x=0.0, pan_y=0.0)
    view_w, view_h, image_w, image_h = 800.0, 600.0, 640.0, 480.0
    min_px, max_px, min_py, max_py = vp.pan_range(view_w, view_h, image_w, image_h)

    assert min_py < max_py  # vertical panning should be enabled here

    # If the image is panned all the way down (max pan_y), the vertical scrollbar
    # should be at the "top" end of its value range.
    vp_down = ViewportState(scale=2.0, pan_x=0.0, pan_y=max_py)
    _, v_val_down, _, _ = vp_down.pan_slider_values(view_w, view_h, image_w, image_h)
    assert v_val_down == 0

    # If the image is panned all the way up (min pan_y), the vertical scrollbar
    # should be at the "bottom" end of its value range.
    vp_up = ViewportState(scale=2.0, pan_x=0.0, pan_y=min_py)
    _, v_val_up, _, _ = vp_up.pan_slider_values(view_w, view_h, image_w, image_h)
    assert v_val_up == 1000

    # And the reverse mapping should hold when setting from slider values.
    vp2 = ViewportState(scale=2.0)
    vp2.pan_from_sliders(0, 0, view_w, view_h, image_w, image_h)
    assert vp2.pan_y == pytest.approx(max_py, abs=1e-6)

    vp3 = ViewportState(scale=2.0)
    vp3.pan_from_sliders(0, 1000, view_w, view_h, image_w, image_h)
    assert vp3.pan_y == pytest.approx(min_py, abs=1e-6)


def test_horizontal_pan_slider_direction_matches_modern_ux():
    """
    UX expectation:
    - dragging the horizontal scrollbar "right" should move the viewport right
      (so `pan_x` should increase).
    """
    vp = ViewportState(scale=2.0, pan_x=0.0, pan_y=0.0)
    view_w, view_h, image_w, image_h = 800.0, 600.0, 640.0, 480.0
    min_px, max_px, min_py, max_py = vp.pan_range(view_w, view_h, image_w, image_h)

    assert min_px < max_px  # horizontal panning should be enabled here

    # If the image is panned all the way right (max pan_x), the horizontal scrollbar
    # should be at the "left" end of its value range.
    vp_right = ViewportState(scale=2.0, pan_x=max_px, pan_y=0.0)
    h_val_right, _, _, _ = vp_right.pan_slider_values(view_w, view_h, image_w, image_h)
    assert h_val_right == 0

    # If the image is panned all the way left (min pan_x), the horizontal scrollbar
    # should be at the "right" end of its value range.
    vp_left = ViewportState(scale=2.0, pan_x=min_px, pan_y=0.0)
    h_val_left, _, _, _ = vp_left.pan_slider_values(view_w, view_h, image_w, image_h)
    assert h_val_left == 1000

    # And the reverse mapping should hold when setting from slider values.
    vp2 = ViewportState(scale=2.0)
    vp2.pan_from_sliders(0, 0, view_w, view_h, image_w, image_h)
    assert vp2.pan_x == pytest.approx(max_px, abs=1e-6)

    vp3 = ViewportState(scale=2.0)
    vp3.pan_from_sliders(1000, 0, view_w, view_h, image_w, image_h)
    assert vp3.pan_x == pytest.approx(min_px, abs=1e-6)
