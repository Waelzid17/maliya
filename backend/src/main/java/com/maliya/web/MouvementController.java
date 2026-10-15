package com.maliya.web;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.maliya.requetes.Requetes;
import com.maliya.service.MouvementService;
import com.maliya.service.MouvementService.NouveauMouvement;

@RestController
@RequestMapping("/api/mouvements")
public class MouvementController {

    private final NamedParameterJdbcTemplate jdbc;
    private final MouvementService service;

    public MouvementController(NamedParameterJdbcTemplate jdbc, MouvementService service) {
        this.jdbc = jdbc;
        this.service = service;
    }

    @GetMapping
    public Map<String, Object> lister(@RequestParam(required = false) Long structureId,
                                      @RequestParam(required = false) Long categorieId,
                                      @RequestParam(required = false) String q,
                                      @RequestParam(defaultValue = "false") boolean aClasser,
                                      @RequestParam(defaultValue = "0") int page,
                                      @RequestParam(defaultValue = "50") int taille) {
        int t = Math.max(1, Math.min(taille, 200));
        MapSqlParameterSource p = new MapSqlParameterSource()
                .addValue("sid", structureId)
                .addValue("cat", categorieId)
                .addValue("q", q == null || q.isBlank() ? null : q.trim())
                .addValue("aClasser", aClasser)
                .addValue("taille", t)
                .addValue("decalage", Math.max(page, 0) * t);
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("elements", jdbc.queryForList(Requetes.MOUVEMENTS, p));
        r.put("total", jdbc.queryForObject(Requetes.MOUVEMENTS_TOTAL, p, Long.class));
        r.put("page", page);
        r.put("taille", t);
        return r;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> creer(@RequestBody NouveauMouvement nouveau) {
        return service.creer(nouveau);
    }

    public record Modification(Long categorieId, Long projetId, Boolean retirerProjet) {
    }

    @PatchMapping("/{id}")
    public Map<String, Object> modifier(@PathVariable Long id, @RequestBody Modification m) {
        return service.modifier(id, m.categorieId(), m.projetId(), Boolean.TRUE.equals(m.retirerProjet()));
    }

    public record Validation(List<Map<String, Object>> propositions) {
    }

    @PostMapping("/valider-propositions")
    public Map<String, Object> validerPropositions(@RequestBody Validation v) {
        int n = service.validerPropositions(v.propositions() == null ? List.of() : v.propositions());
        return Map.of("valides", n);
    }
}
