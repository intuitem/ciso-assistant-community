import pytest
from core.models import Team, Actor
from iam.models import User
from tprm.models import Entity

@pytest.mark.django_db
class TestActorSync:
    """
    Tests ensuring that Actor objects are correctly synchronized with
    User, Team, and Entity objects.
    """

    def test_user_actor_lifecycle(self):
        """
        Verify that creating a User creates an Actor, and deleting the User
        deletes the Actor.
        """
        # Create User
        user = User.objects.create_user(email="test_actor_user@example.com", password="password")
        
        # Check Actor existence
        assert hasattr(user, "actor")
        assert user.actor is not None
        assert Actor.objects.filter(user=user).exists()
        actor_id = user.actor.id

        # Delete User
        user.delete()

        # Check Actor deletion
        assert not Actor.objects.filter(id=actor_id).exists()

    def test_team_actor_lifecycle(self):
        """
        Verify that creating a Team creates an Actor, and deleting the Team
        deletes the Actor.
        """
        # Create Leader User (required for Team)
        leader = User.objects.create_user(email="team_leader@example.com", password="password")

        # Create Team
        team = Team.objects.create(name="Test Team", leader=leader)

        # Check Actor existence
        assert hasattr(team, "actor")
        assert team.actor is not None
        assert Actor.objects.filter(team=team).exists()
        actor_id = team.actor.id

        # Delete Team
        team.delete()

        # Check Actor deletion
        assert not Actor.objects.filter(id=actor_id).exists()

    def test_entity_actor_lifecycle(self):
        """
        Verify that creating an Entity creates an Actor, and deleting the Entity
        deletes the Actor.
        """
        # Create Entity
        entity = Entity.objects.create(name="Test Entity")

        # Check Actor existence
        assert hasattr(entity, "actor")
        assert entity.actor is not None
        assert Actor.objects.filter(entity=entity).exists()
        actor_id = entity.actor.id

        # Delete Entity
        entity.delete()

        # Check Actor deletion
        assert not Actor.objects.filter(id=actor_id).exists()

    def test_user_bulk_create_actor_sync(self):
        """
        Verify that bulk_create for Users also bulk creates Actors.
        """
        users = [
            User(email=f"bulk_user_{i}@example.com")
            for i in range(5)
        ]
        
        # bulk_create
        created_users = User.objects.bulk_create(users)
        
        # Verify Actors
        for user in created_users:
            # Need to refresh from db or query explicitly because .actor might not be populated on the instance immediately 
            # (though normally Django doesn't populate reverse relations on bulk_create return values, 
            # we need to check existence in DB)
            assert Actor.objects.filter(user=user).exists()
            
        assert Actor.objects.filter(user__email__startswith="bulk_user_").count() == 5

    def test_team_bulk_create_actor_sync(self):
        """
        Verify that bulk_create for Teams also bulk creates Actors.
        """
        leader = User.objects.create_user(email="bulk_team_leader@example.com", password="password")
        
        teams = [
            Team(name=f"Bulk Team {i}", leader=leader)
            for i in range(5)
        ]
        
        # bulk_create
        created_teams = Team.objects.bulk_create(teams)
        
        # Verify Actors
        for team in created_teams:
            assert Actor.objects.filter(team=team).exists()

        assert Actor.objects.filter(team__name__startswith="Bulk Team").count() == 5

    def test_entity_bulk_create_actor_sync(self):
        """
        Verify that bulk_create for Entities also bulk creates Actors.
        """
        entities = [
            Entity(name=f"Bulk Entity {i}")
            for i in range(5)
        ]
        
        # bulk_create
        created_entities = Entity.objects.bulk_create(entities)
        
        # Verify Actors
        for entity in created_entities:
            assert Actor.objects.filter(entity=entity).exists()

        assert Actor.objects.filter(entity__name__startswith="Bulk Entity").count() == 5

    def test_actor_uniqueness_constraint(self):
        """
        Verify that an Actor cannot link to multiple objects simultaneously
        (though this is enforced by OneToOneField and DB constraints).
        """
        user = User.objects.create_user(email="constraint_user@example.com", password="password")
        entity = Entity.objects.create(name="constraint_entity")

        user_actor = user.actor
        entity_actor = entity.actor

        # Try to set user_actor's entity to the entity (should fail unique constraint or similar if enforcing logic, 
        # but here we are checking the model constraint manually if we were to create one)
        
        # Actually the constraint is:
        # check=(
        #     Q(user__isnull=False, team__isnull=True, entity__isnull=True)
        #     | Q(user__isnull=True, team__isnull=False, entity__isnull=True)
        #     | Q(user__isnull=True, team__isnull=True, entity__isnull=False)
        # ),
        
        # Let's try to create an invalid actor
        with pytest.raises(Exception): # generic exception as it could be IntegrityError or ValidationError
             Actor.objects.create(user=user, entity=entity)

