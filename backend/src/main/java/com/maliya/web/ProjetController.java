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

/** Projets : budget de dépenses, coût réel, facturé, marge, et date à laquelle le budget sera épuisé. */
@RestController
@RequestMapping("/api/projets")
public class ProjetController {

    private static final BigDecimal CENT = new BigDecimal("100");
    private final NamedParameterJdbcTemplate jdbc;
    private final Horloge horloge;

    public ProjetController(NamedParameterJdbcTemplate jdbc, Horloge horloge) {
        this.jdbc = jdbc;
        this.horloge = horloge;
    }

    @GetMapping
    public List<Map<String, Object>> lister(@RequestParam(required = false) Long structureId) {
        LocalDate ref = horloge.aujourdhui();
        List<Map<String, Object>> lignes = jdbc.queryForList(Requetes.PROJETS,
                new MapSqlParameterSource().addValue("sid", structureId).addValue("ref", ref));
        return lignes.stream().map(l -> enrichir(l, ref)).toList();
    }

    private Map<String, Object> enrichir(Map<String, Object> l, LocalDate ref) {
        Map<String, Object> p = new LinkedHashMap<>(l);
        BigDecimal budget = (BigDecimal) l.get("budget");
        BigDecimal cout = (BigDecimal) l.get("coutReel");
        BigDecimal facture = (BigDecimal) l.get("factureHt");
        BigDecimal rythme = (BigDecimal) l.get("rythmeMensuel");
        BigDecimal marge = facture.subtract(cout);
        p.put("marge", marge);
        p.put("margePct", facture.signum() == 0 ? null : marge.multiply(CENT).divide(facture, 1, RoundingMode.HALF_UP));
        p.put("consommation", budget.signum() == 0 ? null : cout.multiply(CENT).divide(budget, 1, RoundingMode.HALF_UP));
        p.put("interne", l.get("clientId") == null);
        BigDecimal reste = budget.subtract(cout);
        String epuise = null;
        if ("EN_COURS".equals(l.get("statut")) && rythme.signum() > 0 && reste.signum() > 0) {
            long jours = reste.multiply(new BigDecimal("30")).divide(rythme, 0, RoundingMode.HALF_UP).longValue();
            epuise = ref.plusDays(jours).toString();
        }
        p.put("budgetEpuiseVers", epuise);
        return p;
    }
}
