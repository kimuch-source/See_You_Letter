import os
import time
from datetime import datetime
from app import app, db, memo, line_bot_api, TextSendMessage

YOUR_LINE_ID = os.getenv('MY_USER_ID')

def check_and_send_notifications():
    with app.app_context():
        print("【ログ】監視専用ファイルで起動しました！")
        while True:
            try:
                now = datetime.now()
                print(f"【ログ】チェック時刻: {now}")

                memos_to_notify = memo.query.filter(memo.timer <= now).all()
                # --- 以下、送信と削除の処理 ---
                if  memos_to_notify:
                    for m in memos_to_notify:
                        try:
                            #LINE通知を送信
                            line_bot_api.push_message(YOUR_LINE_ID, TextSendMessage(text=f"{m.content}"))
                            print(f"通知成功: {m.content}")
                            
                            db.session.delete(m)
                            print(f"削除中: {m.content}")

                        except Exception as e:
                            print(f"自動通知エラー: {e}")

                    try:
                        db.session.commit()
                        print("全ての通知済みメモを削除完了しました")
                    except Exception as e:
                        db.session.rollback()
                        print(f"DBコミットエラー。ロールバックしました) : {e}")

            except Exception as e:
                print(f"エラー: {e}")

            time.sleep(60)


if __name__ == "__main__":
    check_and_send_notifications()  # スレッドを使わず、直接実行する