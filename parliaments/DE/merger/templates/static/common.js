// js module with common functions
let normalized_data = (data) => {
    return data.map(s => {
        let pi = s.agendaItem.proceedingIndex || 1000;
        pi = pi - (pi >= 1000 ? 1000 : 0);
        return {
            "proceeding": pi,
            "media": (s.agendaItem.mediaIndex || 0),
            "title": s.agendaItem.officialTitle,
            "speaker": s.people[0].label,
            "url": `#speech${s.agendaItem.speechIndex}`,
            "matching": (pi == 0 ? 'media_only' : ((s.agendaItem.mediaIndex || 0) == 0 ? 'proceeding_only' : 'matching')),
            "char_count": s.textContents ? d3.sum(s.textContents.map(tc => d3.sum(tc.textBody.map(tb => tb.text.length)))) : 0,
            "word_count": s.textContents ? d3.sum(s.textContents.map(tc => d3.sum(tc.textBody.map(tb => tb.text.split(' ').length)))) : 0,
            "duration": s.media ? s.media.duration : 0
        }
    });
};
