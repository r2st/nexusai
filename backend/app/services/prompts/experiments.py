"""
Prompt A/B Testing Service

Experimentation framework for prompt optimization:
- Traffic splitting
- Metric tracking
- Statistical significance
- Winner selection
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import hashlib
import logging
import math
import uuid

logger = logging.getLogger(__name__)


class ExperimentStatus(str, Enum):
    """Status of an experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VariantType(str, Enum):
    """Type of prompt variant."""
    CONTROL = "control"
    TREATMENT = "treatment"


@dataclass
class PromptVariant:
    """A variant in an A/B test."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    type: VariantType = VariantType.TREATMENT
    
    # The prompt content
    template: str = ""
    system_prompt: Optional[str] = None
    
    # Traffic allocation (0-100)
    traffic_percentage: float = 50.0
    
    # Metrics
    impressions: int = 0
    conversions: int = 0
    total_latency_ms: int = 0
    total_tokens: int = 0
    
    # Quality scores
    thumbs_up: int = 0
    thumbs_down: int = 0
    
    # Custom metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    @property
    def conversion_rate(self) -> float:
        if self.impressions == 0:
            return 0.0
        return self.conversions / self.impressions
    
    @property
    def avg_latency_ms(self) -> float:
        if self.impressions == 0:
            return 0.0
        return self.total_latency_ms / self.impressions
    
    @property
    def avg_tokens(self) -> float:
        if self.impressions == 0:
            return 0.0
        return self.total_tokens / self.impressions
    
    @property
    def satisfaction_rate(self) -> float:
        total = self.thumbs_up + self.thumbs_down
        if total == 0:
            return 0.5
        return self.thumbs_up / total


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""
    # Traffic settings
    min_sample_size: int = 100
    max_sample_size: int = 10000
    
    # Duration
    max_duration_days: int = 30
    min_duration_days: int = 7
    
    # Statistical settings
    confidence_level: float = 0.95
    minimum_detectable_effect: float = 0.05
    
    # Auto-actions
    auto_stop_on_significance: bool = True
    auto_promote_winner: bool = False
    
    # Targeting
    target_user_percentage: float = 100.0
    target_user_ids: Optional[Set[str]] = None
    exclude_user_ids: Optional[Set[str]] = None


@dataclass
class Experiment:
    """A prompt A/B test experiment."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # Which prompt this experiments on
    prompt_id: str = ""
    
    # Status
    status: ExperimentStatus = ExperimentStatus.DRAFT
    
    # Variants
    control: Optional[PromptVariant] = None
    treatments: List[PromptVariant] = field(default_factory=list)
    
    # Configuration
    config: ExperimentConfig = field(default_factory=ExperimentConfig)
    
    # Primary metric
    primary_metric: str = "conversion_rate"  # conversion_rate, satisfaction_rate, latency
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # Results
    winner_variant_id: Optional[str] = None
    is_significant: bool = False
    p_value: Optional[float] = None
    
    # Metadata
    tenant_id: str = ""
    created_by: str = ""
    tags: List[str] = field(default_factory=list)
    
    @property
    def all_variants(self) -> List[PromptVariant]:
        variants = []
        if self.control:
            variants.append(self.control)
        variants.extend(self.treatments)
        return variants
    
    @property
    def total_impressions(self) -> int:
        return sum(v.impressions for v in self.all_variants)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prompt_id": self.prompt_id,
            "status": self.status.value,
            "primary_metric": self.primary_metric,
            "variants": [
                {
                    "id": v.id,
                    "name": v.name,
                    "type": v.type.value,
                    "traffic_percentage": v.traffic_percentage,
                    "impressions": v.impressions,
                    "conversion_rate": v.conversion_rate,
                    "satisfaction_rate": v.satisfaction_rate,
                    "avg_latency_ms": v.avg_latency_ms,
                }
                for v in self.all_variants
            ],
            "total_impressions": self.total_impressions,
            "is_significant": self.is_significant,
            "p_value": self.p_value,
            "winner_variant_id": self.winner_variant_id,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }


class ExperimentService:
    """
    Manages prompt A/B testing experiments.
    
    Features:
    - Create and manage experiments
    - Traffic splitting
    - Metric tracking
    - Statistical analysis
    - Winner determination
    """
    
    def __init__(
        self,
        storage_backend: Optional[Any] = None,
    ):
        self.storage = storage_backend
        self._experiments: Dict[str, Experiment] = {}
        self._prompt_experiments: Dict[str, str] = {}  # prompt_id -> active experiment_id
    
    def create_experiment(
        self,
        name: str,
        prompt_id: str,
        control_template: str,
        treatment_templates: List[Dict[str, Any]],
        tenant_id: str,
        created_by: str,
        config: Optional[ExperimentConfig] = None,
        primary_metric: str = "conversion_rate",
        description: str = "",
    ) -> Experiment:
        """
        Create a new A/B test experiment.
        
        Args:
            name: Experiment name
            prompt_id: ID of the prompt being tested
            control_template: The control (baseline) prompt template
            treatment_templates: List of treatment variants
            tenant_id: Tenant ID
            created_by: User creating the experiment
            config: Experiment configuration
            primary_metric: Primary metric for winner determination
            description: Description of the experiment
            
        Returns:
            Created Experiment
        """
        # Calculate traffic split
        num_variants = 1 + len(treatment_templates)
        base_traffic = 100.0 / num_variants
        
        # Create control variant
        control = PromptVariant(
            name="Control",
            type=VariantType.CONTROL,
            template=control_template,
            traffic_percentage=base_traffic,
        )
        
        # Create treatment variants
        treatments = []
        for i, treatment in enumerate(treatment_templates):
            variant = PromptVariant(
                name=treatment.get("name", f"Treatment {i+1}"),
                type=VariantType.TREATMENT,
                template=treatment["template"],
                system_prompt=treatment.get("system_prompt"),
                traffic_percentage=treatment.get("traffic_percentage", base_traffic),
            )
            treatments.append(variant)
        
        # Create experiment
        experiment = Experiment(
            name=name,
            description=description,
            prompt_id=prompt_id,
            control=control,
            treatments=treatments,
            config=config or ExperimentConfig(),
            primary_metric=primary_metric,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        
        self._experiments[experiment.id] = experiment
        
        logger.info(f"Created experiment {experiment.id}: {name}")
        return experiment
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False
        
        if experiment.status != ExperimentStatus.DRAFT:
            return False
        
        # Check for existing active experiment on this prompt
        if experiment.prompt_id in self._prompt_experiments:
            existing_id = self._prompt_experiments[experiment.prompt_id]
            existing = self._experiments.get(existing_id)
            if existing and existing.status == ExperimentStatus.RUNNING:
                logger.warning(f"Prompt {experiment.prompt_id} already has an active experiment")
                return False
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.utcnow()
        self._prompt_experiments[experiment.prompt_id] = experiment_id
        
        logger.info(f"Started experiment {experiment_id}")
        return True
    
    def pause_experiment(self, experiment_id: str) -> bool:
        """Pause a running experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return False
        
        experiment.status = ExperimentStatus.PAUSED
        return True
    
    def resume_experiment(self, experiment_id: str) -> bool:
        """Resume a paused experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.PAUSED:
            return False
        
        experiment.status = ExperimentStatus.RUNNING
        return True
    
    def stop_experiment(
        self,
        experiment_id: str,
        select_winner: bool = True,
    ) -> Optional[str]:
        """
        Stop an experiment and optionally select a winner.
        
        Returns:
            Winner variant ID if selected
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None
        
        experiment.status = ExperimentStatus.COMPLETED
        experiment.ended_at = datetime.utcnow()
        
        # Remove from active experiments
        if experiment.prompt_id in self._prompt_experiments:
            del self._prompt_experiments[experiment.prompt_id]
        
        if select_winner:
            winner_id = self._determine_winner(experiment)
            experiment.winner_variant_id = winner_id
            return winner_id
        
        return None
    
    def get_variant_for_user(
        self,
        prompt_id: str,
        user_id: str,
    ) -> Optional[tuple[str, PromptVariant]]:
        """
        Get the variant a user should see.
        
        Uses consistent hashing to ensure same user always gets same variant.
        
        Args:
            prompt_id: Prompt ID
            user_id: User ID
            
        Returns:
            Tuple of (experiment_id, variant) or None if no active experiment
        """
        experiment_id = self._prompt_experiments.get(prompt_id)
        if not experiment_id:
            return None
        
        experiment = self._experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # Check targeting
        config = experiment.config
        if config.target_user_ids and user_id not in config.target_user_ids:
            return None
        if config.exclude_user_ids and user_id in config.exclude_user_ids:
            return None
        
        # Check if user is in experiment sample
        user_hash = int(hashlib.md5(f"{experiment_id}:{user_id}".encode()).hexdigest(), 16)
        if (user_hash % 100) >= config.target_user_percentage:
            return None
        
        # Consistent assignment to variant
        variant = self._assign_variant(experiment, user_id)
        return experiment_id, variant
    
    def _assign_variant(self, experiment: Experiment, user_id: str) -> PromptVariant:
        """Assign user to a variant using consistent hashing."""
        # Create hash for assignment
        hash_input = f"{experiment.id}:{user_id}:variant"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16) % 100
        
        # Walk through variants by traffic percentage
        cumulative = 0.0
        for variant in experiment.all_variants:
            cumulative += variant.traffic_percentage
            if hash_value < cumulative:
                return variant
        
        # Fallback to control
        return experiment.control or experiment.all_variants[0]
    
    def record_impression(
        self,
        experiment_id: str,
        variant_id: str,
        latency_ms: int = 0,
        tokens: int = 0,
    ) -> None:
        """Record an impression for a variant."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return
        
        for variant in experiment.all_variants:
            if variant.id == variant_id:
                variant.impressions += 1
                variant.total_latency_ms += latency_ms
                variant.total_tokens += tokens
                break
        
        # Check if we should auto-stop
        self._check_auto_stop(experiment)
    
    def record_conversion(
        self,
        experiment_id: str,
        variant_id: str,
    ) -> None:
        """Record a conversion for a variant."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return
        
        for variant in experiment.all_variants:
            if variant.id == variant_id:
                variant.conversions += 1
                break
    
    def record_feedback(
        self,
        experiment_id: str,
        variant_id: str,
        is_positive: bool,
    ) -> None:
        """Record user feedback (thumbs up/down)."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return
        
        for variant in experiment.all_variants:
            if variant.id == variant_id:
                if is_positive:
                    variant.thumbs_up += 1
                else:
                    variant.thumbs_down += 1
                break
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get an experiment by ID."""
        return self._experiments.get(experiment_id)
    
    def list_experiments(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[ExperimentStatus] = None,
        prompt_id: Optional[str] = None,
    ) -> List[Experiment]:
        """List experiments with optional filtering."""
        experiments = list(self._experiments.values())
        
        if tenant_id:
            experiments = [e for e in experiments if e.tenant_id == tenant_id]
        if status:
            experiments = [e for e in experiments if e.status == status]
        if prompt_id:
            experiments = [e for e in experiments if e.prompt_id == prompt_id]
        
        return experiments
    
    def get_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed results for an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None
        
        # Calculate statistics
        results = experiment.to_dict()
        
        # Add statistical analysis
        if experiment.control and experiment.treatments:
            control = experiment.control
            
            for treatment in experiment.treatments:
                analysis = self._analyze_variant_pair(
                    control, treatment, experiment.primary_metric
                )
                results[f"analysis_{treatment.id}"] = analysis
        
        return results
    
    def _determine_winner(self, experiment: Experiment) -> Optional[str]:
        """Determine the winning variant."""
        if not experiment.control or not experiment.treatments:
            return None
        
        best_variant = experiment.control
        best_value = self._get_metric_value(experiment.control, experiment.primary_metric)
        
        for treatment in experiment.treatments:
            value = self._get_metric_value(treatment, experiment.primary_metric)
            
            # For latency, lower is better
            if experiment.primary_metric == "latency":
                if value < best_value:
                    best_variant = treatment
                    best_value = value
            else:
                if value > best_value:
                    best_variant = treatment
                    best_value = value
        
        # Check statistical significance
        if experiment.control != best_variant:
            analysis = self._analyze_variant_pair(
                experiment.control,
                best_variant,
                experiment.primary_metric,
            )
            experiment.p_value = analysis.get("p_value")
            experiment.is_significant = analysis.get("is_significant", False)
            
            if experiment.is_significant:
                return best_variant.id
        
        # Return control if no significant winner
        return experiment.control.id
    
    def _get_metric_value(self, variant: PromptVariant, metric: str) -> float:
        """Get a metric value from a variant."""
        if metric == "conversion_rate":
            return variant.conversion_rate
        elif metric == "satisfaction_rate":
            return variant.satisfaction_rate
        elif metric == "latency":
            return variant.avg_latency_ms
        elif metric == "tokens":
            return variant.avg_tokens
        else:
            return variant.custom_metrics.get(metric, 0.0)
    
    def _analyze_variant_pair(
        self,
        control: PromptVariant,
        treatment: PromptVariant,
        metric: str,
    ) -> Dict[str, Any]:
        """Analyze statistical significance between two variants."""
        # Get values
        control_value = self._get_metric_value(control, metric)
        treatment_value = self._get_metric_value(treatment, metric)
        
        # Calculate lift
        if control_value > 0:
            lift = (treatment_value - control_value) / control_value
        else:
            lift = 0.0
        
        # Simple z-test for proportions (conversion/satisfaction)
        if metric in ("conversion_rate", "satisfaction_rate"):
            p_value = self._proportion_z_test(
                control.conversions if metric == "conversion_rate" else control.thumbs_up,
                control.impressions if metric == "conversion_rate" else (control.thumbs_up + control.thumbs_down),
                treatment.conversions if metric == "conversion_rate" else treatment.thumbs_up,
                treatment.impressions if metric == "conversion_rate" else (treatment.thumbs_up + treatment.thumbs_down),
            )
        else:
            # For continuous metrics, use a simple comparison
            p_value = 0.5 if control_value == treatment_value else 0.1
        
        is_significant = p_value < 0.05
        
        return {
            "control_value": control_value,
            "treatment_value": treatment_value,
            "lift": lift,
            "lift_percentage": lift * 100,
            "p_value": p_value,
            "is_significant": is_significant,
            "control_sample_size": control.impressions,
            "treatment_sample_size": treatment.impressions,
        }
    
    def _proportion_z_test(
        self,
        successes1: int,
        n1: int,
        successes2: int,
        n2: int,
    ) -> float:
        """Perform a two-proportion z-test."""
        if n1 == 0 or n2 == 0:
            return 1.0
        
        p1 = successes1 / n1
        p2 = successes2 / n2
        
        # Pooled proportion
        p_pool = (successes1 + successes2) / (n1 + n2)
        
        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        
        if se == 0:
            return 1.0
        
        # Z-score
        z = (p1 - p2) / se
        
        # Two-tailed p-value (approximation)
        p_value = 2 * (1 - self._normal_cdf(abs(z)))
        
        return p_value
    
    def _normal_cdf(self, x: float) -> float:
        """Approximate normal CDF."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def _check_auto_stop(self, experiment: Experiment) -> None:
        """Check if experiment should auto-stop."""
        if experiment.status != ExperimentStatus.RUNNING:
            return
        
        config = experiment.config
        
        # Check max sample size
        if experiment.total_impressions >= config.max_sample_size:
            logger.info(f"Auto-stopping experiment {experiment.id}: max sample size reached")
            self.stop_experiment(experiment.id)
            return
        
        # Check duration
        if experiment.started_at:
            duration = datetime.utcnow() - experiment.started_at
            if duration.days >= config.max_duration_days:
                logger.info(f"Auto-stopping experiment {experiment.id}: max duration reached")
                self.stop_experiment(experiment.id)
                return
        
        # Check for early significance
        if config.auto_stop_on_significance and experiment.total_impressions >= config.min_sample_size:
            if experiment.control and experiment.treatments:
                for treatment in experiment.treatments:
                    analysis = self._analyze_variant_pair(
                        experiment.control,
                        treatment,
                        experiment.primary_metric,
                    )
                    if analysis.get("is_significant"):
                        logger.info(f"Auto-stopping experiment {experiment.id}: significance reached")
                        self.stop_experiment(experiment.id)
                        return
