from rest_framework import serializers

class RecomendacionSerializer(serializers.Serializer):
    track_name = serializers.CharField()
    artists = serializers.CharField()
    album_name = serializers.CharField()
    track_genre = serializers.CharField(required=False, allow_blank=True)
    preview_url = serializers.URLField(required=False, allow_null=True)
