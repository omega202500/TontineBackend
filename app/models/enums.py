import enum

class FrequenceTontine(str, enum.Enum):
    HEBDOMADAIRE = "HEBDOMADAIRE"
    MENSUELLE    = "MENSUELLE"
    BIMENSUELLE  = "BIMENSUELLE"

class StatutTontine(str, enum.Enum):
    ACTIVE    = "ACTIVE"
    SUSPENDUE = "SUSPENDUE"
    CLOTUREE  = "CLOTUREE"

class StatutLot(str, enum.Enum):
    ACTIF    = "ACTIF"
    CLOS     = "CLOS"
    SUSPENDU = "SUSPENDU"

class OptionIntegration(str, enum.Enum):
    ANTICIPEE = "ANTICIPEE"
    DEDUCTION = "DEDUCTION"

class StatutSeance(str, enum.Enum):
    PLANIFIEE = "PLANIFIEE"
    OUVERTE   = "OUVERTE"
    CLOTUREE  = "CLOTUREE"

class StatutPaiement(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE     = "VALIDE"
    REJETE     = "REJETE"
    REMBOURSE  = "REMBOURSE"

class ModePaiement(str, enum.Enum):
    MOBILE_MONEY = "MOBILE_MONEY"
    ESPECES      = "ESPECES"
    MTN          = "MTN"
    ORANGE       = "ORANGE"

class TypeCassation(str, enum.Enum):
    VACANCES_SCOLAIRES = "VACANCES_SCOLAIRES"
    RENTREE_SCOLAIRE   = "RENTREE_SCOLAIRE"
    FETES_FIN_ANNEE    = "FETES_FIN_ANNEE"

class StatutCassation(str, enum.Enum):
    PLANIFIEE = "PLANIFIEE"
    EFFECTUEE = "EFFECTUEE"
    ANNULEE   = "ANNULEE"

class StatutPret(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    APPROUVE   = "APPROUVE"
    REFUSE     = "REFUSE"
    EN_COURS   = "EN_COURS"
    REMBOURSE  = "REMBOURSE"
    DEFAUT     = "DEFAUT"

class MotifAide(str, enum.Enum):
    MALADIE = "MALADIE"
    DECES   = "DECES"
    MARIAGE = "MARIAGE"
    FETE    = "FETE"
    AUTRE   = "AUTRE"

class StatutAide(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    APPROUVEE  = "APPROUVEE"
    REFUSEE    = "REFUSEE"
    VERSEE     = "VERSEE"

class TypeLitige(str, enum.Enum):
    CONTRIBUTION_MANQUANTE = "CONTRIBUTION_MANQUANTE"
    RANG_CONTESTE          = "RANG_CONTESTE"
    PRET_NON_REMBOURSE     = "PRET_NON_REMBOURSE"
    AUTRE                  = "AUTRE"

class StatutLitige(str, enum.Enum):
    OUVERT        = "OUVERT"
    EN_TRAITEMENT = "EN_TRAITEMENT"
    RESOLU        = "RESOLU"
    ESCALADE      = "ESCALADE"

class TypeNotif(str, enum.Enum):
    RAPPEL_COTISATION = "RAPPEL_COTISATION"
    PAIEMENT_CONFIRME = "PAIEMENT_CONFIRME"
    PAIEMENT_REJETE   = "PAIEMENT_REJETE"
    BOUFFEMENT        = "BOUFFEMENT"
    SENTION           = "SENTION"
    REMBOURSEMENT     = "REMBOURSEMENT"
    CASSATION         = "CASSATION"
    DEMANDE_ACCEPTEE  = "DEMANDE_ACCEPTEE"
    DEMANDE_REFUSEE   = "DEMANDE_REFUSEE"
    LITIGE            = "LITIGE"
    AIDE_SENTION      = "AIDE_SENTION"