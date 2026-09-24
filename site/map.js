/* Carte des courses (Leaflet + OpenStreetMap). La page appelle dvMap.render() à chaque recherche. */
(function () {
  var COL = { route: "#2346D1", trail: "#2E7D4F", cross: "#8A5A2B", marche: "#7A4FB5", multi: "#0E7C86" };
  var map, layer, circle, centerMark, lastRefKey = "", firstFit = true, pending = null;

  function init() {
    map = L.map("map", { preferCanvas: true, scrollWheelZoom: false, zoomControl: true }).setView([46.6, 2.4], 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);
    layer = L.layerGroup().addTo(map);
    map.on("click", function (e) { window.dvApi && window.dvApi.setCenter(e.latlng.lat, e.latlng.lng); });
    map.on("focus", function () { map.scrollWheelZoom.enable(); });
    map.on("blur", function () { map.scrollWheelZoom.disable(); });
    map.on("popupopen", function (e) {
      var btn = e.popup.getElement().querySelector("[data-city]");
      if (btn) btn.addEventListener("click", function () {
        map.closePopup();
        window.dvApi.setWhere(btn.getAttribute("data-city"));
      });
    });
  }

  function popup(r) {
    var api = window.dvApi, esc = api.esc;
    var when = api.fmtDate(r.rs) + (r.fin && r.fin !== r.debut ? " → " + api.fmtDate(r.re) : "");
    var shift = r.shift < 0 ? " · " + (-r.shift) + " j avant l'arrivée" : r.shift > 0 ? " · " + r.shift + " j après le départ" : "";
    var dists = (r.formats && r.formats.length) ? r.formats.join(" · ")
      : (r.epreuves || []).filter(function (e) { return e.distance_m; })
          .map(function (e) { return api.fmtDist(e.distance_m); })
          .filter(function (v, i, a) { return a.indexOf(v) === i; }).join(" · ");
    var link = r.site || r.lien;
    return "<b>" + esc(r.nom) + "</b>" +
      '<div class="pp-meta">' + esc(when + shift) + "<br>" + esc(r.ville) + (r.dkm != null ? " · " + Math.round(r.dkm) + " km" : "") + "</div>" +
      (dists ? "<div>" + esc(dists) + "</div>" : "") +
      '<div class="pp-act"><button type="button" data-city="' + esc(r.ville) + '">Chercher autour</button>' +
      (link ? '<a href="' + esc(link) + '" target="_blank" rel="noopener">' + (r.site ? "Site officiel" : "Fiche") + "</a>" : "") + "</div>";
  }

  function render(o) {
    if (!window.L || !document.getElementById("map")) { pending = o; return; }
    if (!map) init();
    layer.clearLayers();
    var pts = [];
    o.items.forEach(function (r) {
      var inside = !o.ref || (r.dkm != null && r.dkm <= o.radius);
      var c = COL[r.type] || COL.route;
      L.circleMarker([r.lat, r.lon], {
        radius: inside ? 7 : 5,
        color: c,
        weight: 2,
        opacity: inside ? 1 : 0.45,
        fillColor: r.shift ? "#FFFFFF" : c,
        fillOpacity: inside ? (r.shift ? 0.9 : 0.85) : 0.3
      }).bindPopup(function () { return popup(r); }).addTo(layer);
      pts.push([r.lat, r.lon]);
    });

    if (circle) { map.removeLayer(circle); circle = null; }
    if (centerMark) { map.removeLayer(centerMark); centerMark = null; }
    if (o.ref) {
      circle = L.circle([o.ref.lat, o.ref.lon], { radius: o.radius * 1000, color: "#15201B", weight: 1, dashArray: "4 4", fill: false, interactive: false }).addTo(map);
      centerMark = L.circleMarker([o.ref.lat, o.ref.lon], { radius: 4, color: "#15201B", weight: 2, fillColor: "#F2C230", fillOpacity: 1, interactive: false }).addTo(map);
    }

    var key = o.ref ? o.ref.lat + "," + o.ref.lon + "," + o.radius : "none";
    if (key !== lastRefKey || firstFit) {
      if (o.ref) map.fitBounds(circle.getBounds(), { padding: [20, 20] });
      else if (pts.length) map.fitBounds(pts, { padding: [20, 20], maxZoom: 9 });
      lastRefKey = key; firstFit = false;
    }
  }

  window.dvMap = { render: render };
  window.addEventListener("load", function () {
    if (pending) { var p = pending; pending = null; render(p); }
    else if (window.dvApi) window.dvApi.ready();
  });
})();
