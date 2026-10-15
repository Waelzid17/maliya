package com.maliya.web;

import java.util.List;
import java.util.Map;

import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.maliya.requetes.Requetes;

@RestController
@RequestMapping("/api")
public class ReferentielController {

    private final NamedParameterJdbcTemplate jdbc;

    public ReferentielController(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/categories")
    public List<Map<String, Object>> categories() {
        return jdbc.queryForList(Requetes.CATEGORIES, new MapSqlParameterSource());
    }

    @GetMapping("/clients")
    public List<Map<String, Object>> clients() {
        return jdbc.queryForList(Requetes.CLIENTS, new MapSqlParameterSource());
    }
}
