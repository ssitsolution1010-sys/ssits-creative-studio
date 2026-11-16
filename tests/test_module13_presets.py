import json
import unittest
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / "ar-vr-interactive.html"
STORAGE_KEY = "ssits-creative-studio-module13-navigator-presets-v1"
def preset(name, query="", typ="all", status="all", sort="original"):
    return dict(name=name, query=query, type=typ, status=status, sort=sort)
def payload(items):
    return dict(schema="ssits.creative-studio.navigator-presets", version=1, presets=items)

class Module13Presets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(HTML.parent)))
        cls.thread = Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/{HTML.name}'
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda err: self.errors.append(str(err)))
        self.page.goto(self.url)
        self.assertEqual(self.page.locator("#objects li").count(), 3)
    def tearDown(self):
        self.assertFalse(self.errors, self.errors)
        self.context.close()
    def save(self, name):
        self.page.fill("#navigatorPresetName", name)
        self.page.click("#saveNavigatorPreset")
    def set_backup(self, items):
        self.page.evaluate("([k,v]) => localStorage.setItem(k,JSON.stringify(v))", [STORAGE_KEY,payload(items)])
    def count(self):
        return self.page.locator("#navigatorPresetSelect option").count()-1
    def test_local_backup_reload_restore(self):
        self.save("One")
        self.page.click("#backupNavigatorPresets")
        self.page.reload()
        self.assertEqual(self.count(),0)
        self.page.click("#restoreNavigatorPresets")
        self.assertEqual(self.count(),1)
        self.assertIn("One",self.page.locator("#navigatorPresetSelect").inner_text())
    def test_readonly_inspect_and_preview(self):
        self.set_backup([preset("Preview", "cube", "cube")])
        self.page.click("#inspectNavigatorPresetBackup")
        self.assertIn("Ready to restore",self.page.locator("#navigatorPresetStatus").inner_text())
        self.page.click("#previewNavigatorPresetBackup")
        self.assertIn("Preview",self.page.locator("#navigatorPresetBackupPreview").inner_text())
        self.assertEqual(self.count(),0)
        self.page.click("#previewNavigatorPresetBackup")
        self.assertTrue(self.page.locator("#navigatorPresetBackupPreview").is_hidden())
    def test_selective_restore(self):
        self.set_backup([preset("First"),preset("Second","ball","sphere")])
        self.page.click("#previewNavigatorPresetBackup")
        self.page.select_option("#navigatorBackupPresetSelect","1")
        self.page.click("#restoreSelectedNavigatorPreset")
        self.assertEqual(self.count(),1)
        self.assertIn("Second",self.page.locator("#navigatorPresetSelect").inner_text())
    def test_selective_duplicate_atomic(self):
        self.save("First")
        self.set_backup([preset("First"),preset("Second")])
        self.page.click("#previewNavigatorPresetBackup")
        self.page.select_option("#navigatorBackupPresetSelect","0")
        self.page.click("#restoreSelectedNavigatorPreset")
        self.assertEqual(self.count(),1)
        self.assertIn("rejected",self.page.locator("#navigatorPresetStatus").inner_text().lower())
    def test_full_restore_duplicate_atomic(self):
        self.save("Existing")
        self.set_backup([preset("Existing"),preset("New")])
        self.page.click("#restoreNavigatorPresets")
        self.assertEqual(self.count(),1)
    def test_capacity_atomic(self):
        for i in range(10):self.save(f"Session-{i}")
        self.set_backup([preset("Extra")])
        self.page.click("#restoreNavigatorPresets")
        self.assertEqual(self.count(),10)
    def test_malformed_backup_rejected(self):
        self.page.evaluate("([k,v]) => localStorage.setItem(k,v)",[STORAGE_KEY,'{"bad":true}'])
        self.page.click("#inspectNavigatorPresetBackup")
        self.assertIn("failed",self.page.locator("#navigatorPresetStatus").inner_text().lower())
        self.assertEqual(self.count(),0)
    def test_clear_cancel_and_confirm(self):
        self.save("Session")
        self.set_backup([preset("Backup")])
        self.page.on("dialog",lambda dialog: dialog.dismiss())
        self.page.click("#clearNavigatorPresetBackup")
        self.assertIsNotNone(self.page.evaluate("k => localStorage.getItem(k)",STORAGE_KEY))
        self.page.remove_all_listeners("dialog")
        self.page.on("dialog",lambda dialog: dialog.accept())
        self.page.click("#clearNavigatorPresetBackup")
        self.assertIsNone(self.page.evaluate("k => localStorage.getItem(k)",STORAGE_KEY))
        self.assertEqual(self.count(),1)
    def test_scene_renderer_and_undo(self):
        self.page.click("#rendererMode")
        self.page.click("#addCube")
        self.assertIn("4 objects",self.page.locator("#sceneStats").inner_text())
        self.page.wait_for_timeout(150)
        self.page.click("#undoEdit")
        self.assertIn("3 objects",self.page.locator("#sceneStats").inner_text())
if __name__=="__main__":
    unittest.main(verbosity=2)
