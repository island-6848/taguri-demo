"""原作の国（起案者の指示 2026-10-16「韓国原作とかは気になる」「A」、origin-korea-in-catalogue）。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import user_recommender as UR  # noqa: E402

KOREA = ("#原作の国", "韓国")


class KoreanOriginTest(unittest.TestCase):
    def tags(self, title, credits):
        return UR.stage_tags(title, [], credits)

    def test_a_korean_writer_or_composer_marks_the_work(self):
        self.assertIn(KOREA, self.tags("秘密の花園", [("脚本", "キム・ソルジ"), ("作曲", "カン・ハニム"), ("翻訳・訳詞", "吉田衣里")]))
        self.assertIn(KOREA, self.tags("私に会いに来て", [("原作", "キム・グァンリム"), ("翻訳", "後藤温子")]))
        self.assertIn(KOREA, self.tags("初魂", [("脚本・作詞", "이희준")]))
        self.assertIn(KOREA, self.tags("초혼 チョホン", [("演出", "日本人")]))

    def test_western_names_and_korean_performers_do_not(self):
        # Anne Chislett / John Du Prez / Harvey Fierstein / Benjamin Britten / a Korean actor in the cast.
        self.assertNotIn(KOREA, self.tags("THE TOMORROW BOX", [("作", "アン・チスレット")]))
        self.assertNotIn(KOREA, self.tags("SPAMALOT", [("作曲", "ジョン・ドゥ")]))
        self.assertNotIn(KOREA, self.tags("ラ・カージュ", [("脚本", "ハーヴェイ・ファイアスタイン")]))
        self.assertNotIn(KOREA, self.tags("マイム", [("脚本", "ハン・ヴォルフガング")]))
        self.assertNotIn(KOREA, self.tags("祭", [("出演", "이동훈"), ("出演", "キム・ソルジ"), ("脚本", "山田")]))

    def test_it_is_a_content_kind(self):
        self.assertIn("#原作の国", UR.CONTENT_AXES)


if __name__ == "__main__":
    unittest.main()
