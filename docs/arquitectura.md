# Arquitectura del Intérprete Lattice Encrypt

Este diagrama describe la arquitectura general del proyecto, mostrando cómo se conectan los módulos principales y el despachador dinámico. Utilizando como ejemplo la operación `VECTOR(1,2) SUMA VECTOR(3,4)`.

```mermaid
graph TD
    %% Estilos
    classDef user fill:#FFDDC1,stroke:#333,stroke-width:2px,color:black;
    classDef core fill:#D4F0F0,stroke:#333,stroke-width:2px,color:black;
    classDef json fill:#C8E6C9,stroke:#333,stroke-width:2px,color:black;
    classDef plugin fill:#E1BEE7,stroke:#333,stroke-width:2px,color:black;

    %% Nodos Principales
    U(( Usuario / Consola)):::user
    R[ Runner.py<br>Punto de Entrada]:::core
    L[ LatticeLexico.py<br>Analizador Léxico]:::core
    S[ LatticeSintactico.py<br>Despachador Dinámico]:::core
    J[( reglas.json)]:::json

    %% Carpeta de reglas
    subgraph "Plugins Matemáticos"
        direction LR
        RB[ReglasBase.py]:::plugin
        RR[ReglasRuido.py]:::plugin
        RT[ReglasTexto.py]:::plugin
        RA[ReglasAritmetica.py]:::plugin
        RC[ReglasComparacion.py]:::plugin
        RL[ReglasLattice.py]:::plugin
    end

    %% Relaciones
    U -->|1. Escribe Comando| R
    R -->|2. Texto| L
    L --->|3. Tokens| R
    
    %% Alargamos esta flecha para que la curva sea diferente y no choque
    R ---->|4. Envía Tokens| S
    
    S -->|5. Lee Configuración| J
    J -.->|Indica archivo a importar| S

    S -->|6. Importa y Ejecuta| RB
    S -->|6. Importa y Ejecuta| RR
    S -->|6. Importa y Ejecuta| RT
    S -->|6. Importa y Ejecuta| RA
    S -->|6. Importa y Ejecuta| RC
    S -->|6. Importa y Ejecuta| RL

    RB -.->|7. Retorna cálculo| S
    S -.->|8. Resultado| R
    R -.->|9. Imprime consola| U
```

## Vista completa: consola, servidor web, variables y cifrado

Ademas de la consola, el interprete se usa desde un servidor web (FastAPI) que sirve el editor y ejecuta cada programa en un proceso aparte con limite de tiempo. El analizador sintactico guarda las variables en un `Entorno` (tabla de simbolos), y `ReglasLattice.py` delega el cifrado en `core/cripto/`.

```mermaid
graph TD
    classDef user fill:#FFDDC1,stroke:#333,stroke-width:2px,color:black;
    classDef core fill:#D4F0F0,stroke:#333,stroke-width:2px,color:black;
    classDef json fill:#C8E6C9,stroke:#333,stroke-width:2px,color:black;
    classDef plugin fill:#E1BEE7,stroke:#333,stroke-width:2px,color:black;
    classDef cripto fill:#FFF3B0,stroke:#333,stroke-width:2px,color:black;

    U(( Usuario)):::user
    WEB[ web/<br>Editor en el navegador]:::user
    R[ Runner.py<br>Consola]:::core
    SV[ servidor.py<br>FastAPI: /iniciar, /ejecutar, /editor]:::core
    EJ[ core/ejecutor.py<br>Proceso hijo con TIEMPO_LIMITE]:::core
    IA[ core/interpreteArchivo.py<br>Linea, archivo .le o programa]:::core
    L[ LatticeLexico.py]:::core
    S[ LatticeSintactico.py<br>Asignacion, KEYGEN y despacho]:::core
    E[( core/entorno.py<br>Variables)]:::json
    J[( reglas.json)]:::json

    subgraph "Reglas"
        RV[ReglasBase / Aritmetica / Comparacion / Ruido / Texto]:::plugin
        RL[ReglasLattice.py<br>CIFRAR / DESCIFRAR]:::plugin
    end

    subgraph "core/cripto"
        FR[frodo.py<br>FrodoPKE-640 con numpy]:::cripto
        MK[mlkem.py<br>ML-KEM-768 + AES-256-GCM]:::cripto
        VA[valores.py<br>ParClaves y Cifrado]:::cripto
    end

    U --> R
    U --> WEB
    WEB -->|HTTP| SV
    SV --> EJ
    EJ --> IA
    R --> IA
    IA -->|texto| L
    IA -->|tokens + entorno| S
    S <-->|definir / obtener| E
    S -->|lee| J
    S --> RV
    S --> RL
    S -->|KEYGEN LWE o MLKEM| RL
    RL --> FR
    RL --> MK
    RL --> VA
```

## Secuencia del cifrado

```mermaid
sequenceDiagram
    participant P as Programa .le
    participant S as LatticeSintactico
    participant E as Entorno
    participant RL as ReglasLattice
    participant C as core/cripto (frodo o mlkem)

    P->>S: CLAVES = KEYGEN MLKEM
    S->>RL: generar_claves("MLKEM")
    RL->>C: generar_claves()
    C-->>RL: (publica, privada)
    RL-->>S: ParClaves
    S->>E: definir("CLAVES", ParClaves)

    P->>S: X = TEXTO "HOLA" CIFRAR CLAVES
    S->>E: obtener("CLAVES")
    S->>RL: CIFRAR("HOLA", claves)
    RL->>C: cifrar_texto(claves.publica, "HOLA")
    C-->>RL: criptograma
    RL-->>S: Cifrado
    S->>E: definir("X", Cifrado)

    P->>S: X DESCIFRAR CLAVES
    S->>RL: DESCIFRAR(cifrado, claves)
    RL->>C: descifrar_texto(claves.privada, datos)
    C-->>RL: "HOLA"
    RL-->>S: "HOLA"
```

Al imprimir o devolver por la API, `ParClaves` y `Cifrado` solo muestran un resumen (`<CLAVES ML-KEM-768>`); el material de clave nunca sale del interprete.
