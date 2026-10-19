// The complete form is part of the screen response, before opening the dialog.
export function registerDialogHtml() {
  return '<dialog id="register-search-dialog" class="register-search-dialog" aria-labelledby="rs-heading">'
    + '<div class="rs-head"><h2 id="rs-heading">公演の詳細検索</h2><button type="button" data-rs-close>閉じる</button></div>'
    + '<p>公演名は2文字以上、先頭から入力してください。団体名・劇場・上演日程で絞り込めます。</p>'
    + '<form class="rs-form"><label class="fld"><span class="fl">公演名</span><input name="q" maxlength="120" placeholder="例：夜の果て" required autofocus></label>'
    + '<label class="fld"><span class="fl">団体名<small>任意</small></span><input name="group" maxlength="80" placeholder="例：劇団四季"></label>'
    + '<label class="fld"><span class="fl">劇場<small>任意</small></span><input name="venue" maxlength="80" placeholder="例：本多劇場"></label>'
    + '<fieldset class="rs-schedule"><legend>上演日程（任意）</legend>'
    + '<label class="fld"><span class="fl">指定の細かさ</span><select name="schedule_precision"><option value="none">指定なし</option>'
    + '<option value="month">月</option><option value="monthday">月日</option><option value="year">年</option>'
    + '<option value="yearmonth">年月</option><option value="date">年月日</option></select></label>'
    + '<div class="rs-schedule-fields"><label class="fld" hidden><span class="fl">年</span><input name="schedule_year" type="number" min="1" max="9999" step="1" inputmode="numeric" placeholder="例：2026" disabled></label>'
    + '<label class="fld" hidden><span class="fl">月</span><select name="schedule_month" disabled><option value="">月を選ぶ</option>'
    + Array.from({length: 12}, (_, i) => `<option value="${i + 1}">${i + 1}月</option>`).join('') + '</select></label>'
    + '<label class="fld" hidden><span class="fl">日</span><select name="schedule_day" disabled><option value="">日を選ぶ</option>'
    + Array.from({length: 31}, (_, i) => `<option value="${i + 1}">${i + 1}日</option>`).join('') + '</select></label></div>'
    + '<p class="note">指定した月・日・年に、上演期間が重なる公演を探します。月・月日だけなら年は問いません。</p></fieldset>'
    + '<button type="submit" class="primary">検索する</button></form>'
    + '<p class="rs-status" role="status" aria-live="polite">条件を入れて「検索する」を押してください。</p><div class="sug rs-results"></div>'
    + '</dialog>';
}
