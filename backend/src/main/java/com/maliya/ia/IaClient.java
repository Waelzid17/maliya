package com.maliya.ia;

import java.math.BigDecimal;
import java.net.URI;
import java.util.Map;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/** Client HTTP du service IA (FastAPI). Le backend reste utilisable si l'IA est arrêtée. */
@Component
public class IaClient {

    private static final Logger LOG = LoggerFactory.getLogger(IaClient.class);
    private static final ParameterizedTypeReference<Map<String, Object>> CARTE = new ParameterizedTypeReference<>() {
    };

    private final String base;
    private final RestClient client;

    public IaClient(@Value("${maliya.ia-url}") String base) {
        this.base = base.endsWith("/") ? base.substring(0, base.length() - 1) : base;
        SimpleClientHttpRequestFactory fabrique = new SimpleClientHttpRequestFactory();
        fabrique.setConnectTimeout(3000);
        fabrique.setReadTimeout(90000);
        this.client = RestClient.builder().requestFactory(fabrique).build();
    }

    /** Propose une catégorie pour un libellé bancaire. Vide si l'IA ne répond pas. */
    public Optional<Map<String, Object>> categoriser(String libelle, BigDecimal montant) {
        try {
            Map<String, Object> r = client.post()
                    .uri(URI.create(base + "/categoriser"))
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of("libelle", libelle, "montant", montant))
                    .retrieve()
                    .body(CARTE);
            return Optional.ofNullable(r);
        } catch (RestClientException e) {
            LOG.warn("Catégorisation IA indisponible : {}", e.getMessage());
            return Optional.empty();
        }
    }

    /** Relaye un appel brut (utilisé par le proxy /api/ia/**). Le statut et le JSON de l'IA sont conservés. */
    public ResponseEntity<String> relayer(String methode, String cheminEtRequete, String corps) {
        RestClient.RequestBodySpec spec = client.method(HttpMethod.valueOf(methode))
                .uri(URI.create(base + cheminEtRequete));
        if (corps != null && !corps.isBlank()) {
            spec = spec.contentType(MediaType.APPLICATION_JSON).body(corps);
        }
        return spec.retrieve()
                .onStatus(statut -> true, (requete, reponse) -> {
                    // on laisse passer les erreurs de l'IA telles quelles
                })
                .toEntity(String.class);
    }
}
