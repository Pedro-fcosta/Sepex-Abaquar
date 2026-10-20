import info.openrocket.core.document.OpenRocketDocument;
import info.openrocket.core.document.Simulation;
import info.openrocket.core.document.StorageOptions;
import info.openrocket.core.file.GeneralRocketLoader;
import info.openrocket.core.file.openrocket.OpenRocketSaver;
import info.openrocket.core.logging.ErrorSet;
import info.openrocket.core.logging.WarningSet;
import info.openrocket.core.simulation.FlightData;
import info.openrocket.core.simulation.FlightDataBranch;
import info.openrocket.core.simulation.FlightDataType;
import info.openrocket.core.simulation.FlightEvent;
import info.openrocket.core.startup.OpenRocketCore;

import java.io.BufferedWriter;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;
import java.util.stream.Stream;

/** Executa arquivos ORK no motor real do OpenRocket 24.12 e exporta CSV para o ABAQUAR. */
public final class GerarVoos {
    private static final FlightDataType[] COLUNAS = {
        FlightDataType.TYPE_TIME,
        FlightDataType.TYPE_ALTITUDE,
        FlightDataType.TYPE_VELOCITY_TOTAL,
        FlightDataType.TYPE_ACCELERATION_TOTAL,
        FlightDataType.TYPE_CG_LOCATION,
        FlightDataType.TYPE_CP_LOCATION,
        FlightDataType.TYPE_STABILITY
    };

    private GerarVoos() {}

    private static String numero(Double valor) {
        return valor == null || !Double.isFinite(valor) ? "" : String.format(Locale.ROOT, "%.9g", valor);
    }

    private static void processar(Path entrada, Path raizEntrada, Path raizOrk, Path raizCsv, int semente) throws Exception {
        Path relativo = raizEntrada.relativize(entrada);
        Path ork = raizOrk.resolve(relativo);
        Path csv = raizCsv.resolve(relativo.toString().replaceFirst("(?i)\\.ork$", ".csv"));
        Files.createDirectories(ork.getParent());
        Files.createDirectories(csv.getParent());

        OpenRocketDocument documento = new GeneralRocketLoader(entrada.toFile()).load();
        if (documento.getSimulationCount() != 1) {
            throw new IllegalStateException(entrada + ": esperado exatamente um voo");
        }
        Simulation simulacao = documento.getSimulation(0);
        simulacao.getOptions().setRandomSeed(semente);
        // OpenRocket 24.12 não persiste a semente no ORK. Vento constante
        // mantém os resultados reproduzíveis também ao reabrir o modelo.
        simulacao.getOptions().setWindSpeedDeviation(0.0);
        simulacao.getOptions().setWindTurbulenceIntensity(0.0);
        simulacao.simulate();
        if (simulacao.getStatus() != Simulation.Status.UPTODATE && simulacao.getStatus() != Simulation.Status.ABORTED) {
            throw new IllegalStateException(entrada + ": simulação encerrada com status " + simulacao.getStatus());
        }
        FlightData dados = simulacao.getSimulatedData();
        if (dados == null || dados.getBranchCount() == 0) {
            throw new IllegalStateException(entrada + ": OpenRocket não gerou série temporal");
        }
        FlightDataBranch serie = dados.getBranch(0);
        if (serie.getLength() < 2) {
            throw new IllegalStateException(entrada + ": série temporal incompleta");
        }

        try (BufferedWriter saida = Files.newBufferedWriter(csv, StandardCharsets.UTF_8)) {
            saida.write("# " + entrada.getFileName().toString().replaceFirst("(?i)\\.ork$", "") + " (OpenRocket 24.12)\n");
            saida.write("# Simulation warnings:\n");
            dados.getWarningSet().forEach(aviso -> {
                try {
                    saida.write("#   " + aviso.toString().replace('\n', ' ') + "\n");
                } catch (java.io.IOException erro) {
                    throw new java.io.UncheckedIOException(erro);
                }
            });
            for (FlightEvent evento : serie.getEvents()) {
                if (evento.getType() == FlightEvent.Type.SIM_ABORT) {
                    saida.write("#   Simulação interrompida em " + numero(evento.getTime())
                            + " s: " + String.valueOf(evento.getData()) + ". Resultado parcial.\n");
                }
            }
            saida.write("Time (s),Altitude (m),Total velocity (m/s),Total acceleration (m/s2),CG location (m),CP location (m),Stability margin (cal)\n");
            for (int i = 0; i < serie.getLength(); i++) {
                for (int j = 0; j < COLUNAS.length; j++) {
                    if (j > 0) saida.write(',');
                    saida.write(numero(serie.getByIndex(COLUNAS[j], i)));
                }
                saida.write('\n');
            }
        }

        StorageOptions opcoes = documento.getDefaultStorageOptions().clone();
        opcoes.setSaveSimulationData(true);
        try (OutputStream saida = Files.newOutputStream(ork)) {
            new OpenRocketSaver().save(saida, documento, opcoes, new WarningSet(), new ErrorSet());
        }
        System.out.printf(Locale.ROOT, "%s: %.3f m; %d pontos; %s%n", relativo,
                dados.getMaxAltitude(), serie.getLength(), simulacao.getStatus().name());
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            System.err.println("Uso: GerarVoos ENTRADA_ORK DIRETORIO_ORK DIRETORIO_CSV SEMENTE");
            System.exit(2);
        }
        Path raizEntrada = Path.of(args[0]).toAbsolutePath();
        Path raizOrk = Path.of(args[1]).toAbsolutePath();
        Path raizCsv = Path.of(args[2]).toAbsolutePath();
        int semente = Integer.parseInt(args[3]);
        OpenRocketCore.initialize();
        try (Stream<Path> arquivos = Files.walk(raizEntrada)) {
            for (Path entrada : arquivos.filter(p -> p.toString().toLowerCase(Locale.ROOT).endsWith(".ork")).sorted().toList()) {
                processar(entrada, raizEntrada, raizOrk, raizCsv, semente);
            }
        }
    }
}
