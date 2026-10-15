package com.maliya.config;

import java.time.LocalDate;
import java.time.ZoneId;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** La date « d'aujourd'hui » pour toute l'application (figée en mode démo). */
@Component
public class Horloge {

    private static final ZoneId CASABLANCA = ZoneId.of("Africa/Casablanca");
    private final String dateReference;

    public Horloge(@Value("${maliya.date-reference:}") String dateReference) {
        this.dateReference = dateReference == null ? "" : dateReference.trim();
    }

    public LocalDate aujourdhui() {
        return dateReference.isEmpty() ? LocalDate.now(CASABLANCA) : LocalDate.parse(dateReference);
    }
}
