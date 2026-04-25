//ハンバーガーメニュー
let nav = document.querySelector("#navArea");
let btn = document.querySelector(".toggle-btn");
let mask = document.querySelector("#mask");
btn.onclick = () => {
    nav.classList.toggle("open");
};
mask.onclick = () => {
    nav.classList.toggle("open");
};



//時間入力パネル
const showBtn = document.getElementById('show-btn');
const cancellBtn = document.getElementById('cancell-btn'); 
const panel = document.getElementById('time-panel');

if (showBtn) {
    showBtn.addEventListener('click', function(event) {
        event.preventDefault(); // リロード防止
        panel.style.display = 'block'; // パネルを表示
        console.log("表示ボタンが正しく動作しました");
    });}

if (cancellBtn) {
    cancellBtn.addEventListener('click', function(event) {
        event.preventDefault(); // リロード防止
        panel.style.display = 'none'; // パネルを隠す
        console.log("キャンセルボタンが正しく動作しました");
    });
}