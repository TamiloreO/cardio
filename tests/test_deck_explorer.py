"""Test DeckExplorer class and mapview integration."""

import ast


class TestMapViewDeckExplorerIntegration:
    """Test that mapview correctly integrates deck explorer."""
    
    def test_mapview_has_show_deck_explorer_method(self):
        with open('cardio/tui/mapview.py') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'TUIMapView':
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                assert 'show_deck_explorer' in methods
    
    def test_mapview_imports_deck_explorer(self):
        with open('cardio/tui/mapview.py') as f:
            content = f.read()
        assert 'from .deck_explorer import DeckExplorer' in content
    
    def test_mapview_handles_d_key(self):
        with open('cardio/tui/mapview.py') as f:
            content = f.read()
        assert "ord('d')" in content or 'ord("d")' in content
        assert "ord('D')" in content or 'ord("D")' in content

    def test_mapview_stores_humanplayer(self):
        with open('cardio/tui/mapview.py') as f:
            content = f.read()
        assert 'self.humanplayer = humanplayer' in content


class TestDeckExplorerStructure:
    """Test that deck explorer module has correct structure."""
    
    def test_deck_explorer_class_exists(self):
        with open('cardio/tui/deck_explorer.py') as f:
            tree = ast.parse(f.read())
        
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert 'DeckExplorer' in classes
    
    def test_deck_explorer_has_required_methods(self):
        with open('cardio/tui/deck_explorer.py') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'DeckExplorer':
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                required = ['__init__', 'run', 'redraw', 'draw_cards', 'draw_tabs', 
                           'switch_tab', 'move_cursor', 'ensure_cursor_visible']
                for method in required:
                    assert method in methods, f"Missing method: {method}"
    
    def test_deck_explorer_has_current_deck_property(self):
        with open('cardio/tui/deck_explorer.py') as f:
            content = f.read()
        assert 'def current_deck' in content
    
    def test_deck_explorer_has_current_cards_property(self):
        with open('cardio/tui/deck_explorer.py') as f:
            content = f.read()
        assert 'def current_cards' in content
    
    def test_deck_explorer_handles_escape_key(self):
        with open('cardio/tui/deck_explorer.py') as f:
            content = f.read()
        assert 'Screen.KEY_ESCAPE' in content
    
    def test_deck_explorer_handles_d_key_to_close(self):
        with open('cardio/tui/deck_explorer.py') as f:
            content = f.read()
        assert "ord('d')" in content or 'ord("d")' in content
    
    def test_deck_explorer_handles_arrow_keys(self):
        with open('cardio/tui/deck_explorer.py') as f:
            content = f.read()
        assert 'Screen.KEY_LEFT' in content
        assert 'Screen.KEY_RIGHT' in content
        assert 'Screen.KEY_UP' in content
        assert 'Screen.KEY_DOWN' in content
    
    def test_deck_explorer_handles_tab_key(self):
        with open('cardio/tui/deck_explorer.py') as f:
            content = f.read()
        assert 'Screen.KEY_TAB' in content
