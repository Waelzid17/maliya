package com.maliya.web;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.ResourceAccessException;

import com.maliya.ia.IaClient;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Le front ne parle qu'au backend. Tout ce qui commence par /api/ia/ est relayé au service IA :
 * briefing, prévision, anomalies, RCA, copilote, simulation, saisie naturelle, relances…
 */
@RestController
@RequestMapping("/api/ia")
public class IaController {

    private static final String PREFIXE = "/api/ia";
    private final IaClient ia;

    public IaController(IaClient ia) {
        this.ia = ia;
    }

    @RequestMapping(value = "/**", method = {RequestMethod.GET, RequestMethod.POST})
    public ResponseEntity<String> relayer(HttpServletRequest requete, @RequestBody(required = false) String corps) {
        String chemin = requete.getRequestURI().substring(requete.getContextPath().length() + PREFIXE.length());
        String parametres = requete.getQueryString();
        String cible = chemin + (parametres == null ? "" : "?" + parametres);
        try {
            ResponseEntity<String> r = ia.relayer(requete.getMethod(), cible, corps);
            return ResponseEntity.status(r.getStatusCode()).contentType(MediaType.APPLICATION_JSON).body(r.getBody());
        } catch (ResourceAccessException e) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).contentType(MediaType.APPLICATION_JSON)
                    .body("{\"message\":\"Le service IA ne répond pas. Vérifie qu'il tourne (docker compose ps).\"}");
        }
    }
}
