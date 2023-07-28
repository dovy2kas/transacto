const socketas = io.connect(`https://${window.location.hostname}/main`);

const news_container = document.getElementById("news_container");
const news_circle = document.getElementById("news_circle");
news_circle.style.visibility = "hidden";

function update_news_status() {
    socketas.emit('news_status');
}

socketas.on('connect', function() {
    socketas.emit('get_news');
})

socketas.on('add_news', function(message) {
    const card = document.createElement("div");
    card.classList.add("card");
    const card_body = document.createElement("div");
    card_body.classList.add("card-body");
    card_body.innerHTML = message;
    card.appendChild(card_body);
    news_container.appendChild(card);
});

socketas.on('news_unseen', function() {
    console.log('wtf')
    news_circle.style.visibility = "visible";
});
