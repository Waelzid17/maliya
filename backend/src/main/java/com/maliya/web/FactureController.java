package com.maliya.web;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.maliya.config.Horloge;
import com.maliya.requetes.Requetes;
import com.maliya.service.FactureService;
import com.maliya.service.FactureService.NouvelleFacture;

@RestController
@RequestMapping("/api/factures")
public class FactureController {

    private final NamedParameterJdbcTemplate jdbc;
    private final FactureService service;
    private final Horloge horloge;

    public FactureController(NamedParameterJdbcTemplate jdbc, FactureService service, Horloge horloge) {
        this.jdbc = jdbc;
        this.service = service;
        this.horloge = horloge;
    }

    /** etat : OUVERTES, PAYEES ou vide pour tout. */
    @GetMapping
    public List<Map<String, Object>> lister(@RequestParam(required = false) Long structureId,
                                            @RequestParam(required = false) String etat) {
        return jdbc.queryForList(Requetes.FACTURES, new MapSqlParameterSource()
                .addValue("sid", structureId)
                .addValue("etat", etat == null || etat.isBlank() ? null : etat.toUpperCase())
                .addValue("ref", horloge.aujourdhui()));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> creer(@RequestBody NouvelleFacture n) {
        return service.resume(service.creer(n));
    }

    public record Encaissement(LocalDate date) {
    }

    @PostMapping("/{id}/encaisser")
    public Map<String, Object> encaisser(@PathVariable Long id, @RequestBody(required = false) Encaissement e) {
        return service.resume(service.encaisser(id, e == null ? null : e.date()));
    }
}
