package com.maliya.web;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.maliya.config.Horloge;
import com.maliya.requetes.Requetes;

/** La page « Aujourd'hui » : soldes, mois en cours, courbe sur 12 mois, postes de dépense, factures. */
@RestController
@RequestMapping("/api")
public class TableauDeBordController {

    private final NamedParameterJdbcTemplate jdbc;
    private final Horloge horloge;

    public TableauDeBordController(NamedParameterJdbcTemplate jdbc, Horloge horloge) {
        this.jdbc = jdbc;
        this.horloge = horloge;
    }

    @GetMapping("/structures")
    public List<Map<String, Object>> structures() {
        return jdbc.queryForList(Requetes.SOLDES, new MapSqlParameterSource());
    }

    @GetMapping("/tableau-de-bord")
    public Map<String, Object> tableauDeBord(@RequestParam(required = false) Long structureId) {
        LocalDate ref = horloge.aujourdhui();
        LocalDate debutMois = ref.withDayOfMonth(1);
        LocalDate debutPrec = debutMois.minusMonths(1);
        LocalDate memeJourPrec = debutPrec.plusDays(Math.min(ref.getDayOfMonth(), debutPrec.lengthOfMonth()) - 1L);

        MapSqlParameterSource p = new MapSqlParameterSource()
                .addValue("sid", structureId)
                .addValue("ref", ref);

        List<Map<String, Object>> soldes = jdbc.queryForList(Requetes.SOLDES, new MapSqlParameterSource());
        BigDecimal total = soldes.stream()
                .filter(s -> structureId == null || structureId.equals(((Number) s.get("id")).longValue()))
                .map(s -> (BigDecimal) s.get("solde"))
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        Map<String, Object> mois = jdbc.queryForMap(Requetes.FLUX_PERIODE,
                new MapSqlParameterSource(p.getValues()).addValue("debut", debutMois).addValue("fin", ref));
        Map<String, Object> moisPrec = jdbc.queryForMap(Requetes.FLUX_PERIODE,
                new MapSqlParameterSource(p.getValues()).addValue("debut", debutPrec).addValue("fin", memeJourPrec));

        BigDecimal sortiesMoyennes = jdbc.queryForObject(Requetes.SORTIES_MOYENNES_3_MOIS, p, BigDecimal.class);
        BigDecimal couverture = sortiesMoyennes == null || sortiesMoyennes.signum() == 0 ? null
                : total.divide(sortiesMoyennes, 1, RoundingMode.HALF_UP);

        Map<String, Object> resultat = new LinkedHashMap<>();
        resultat.put("dateReference", ref.toString());
        resultat.put("structureId", structureId);
        resultat.put("soldes", soldes);
        resultat.put("total", total);
        resultat.put("moisEnCours", Map.of(
                "entrees", mois.get("entrees"), "sorties", mois.get("sorties"),
                "entreesPrecedent", moisPrec.get("entrees"), "sortiesPrecedent", moisPrec.get("sorties")));
        resultat.put("serie", jdbc.queryForList(Requetes.SERIE_MENSUELLE, p));
        resultat.put("depensesParCategorie", jdbc.queryForList(Requetes.DEPENSES_PAR_CATEGORIE,
                new MapSqlParameterSource(p.getValues()).addValue("debut", debutMois).addValue("fin", ref)));
        resultat.put("factures", jdbc.queryForMap(Requetes.FACTURES_RESUME, p));
        resultat.put("moisDeDepensesCouverts", couverture);
        return resultat;
    }
}
