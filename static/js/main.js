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

function showTimerModal() {
    let hours = prompt('何時間後に送りますか？');
    let minutes = prompt('何分後に送りますか？');
    let totalMinutes = (hours * 60) + parseInt(minutes);
    document.getElementById('timer').value = totalMinutes;
    document.getElementById('memoForm').submit();
}